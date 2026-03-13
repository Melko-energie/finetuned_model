#!/usr/bin/env python3
"""
Training script for LayoutLMv3 with LoRA
Corrections J5:
- Suppression prepare_model_for_kbit_training (gelait les gradients)
- Ajout class weights (corrige déséquilibre O vs entités)
- fp16=False forcé (CPU uniquement)
"""

import os
import json
import torch
from transformers import (
    LayoutLMv3ForTokenClassification,
    LayoutLMv3Processor,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
from peft import (
    get_peft_model,
    LoraConfig,
    TaskType,
)
from datasets import load_from_disk
import evaluate
import numpy as np
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    model_name: str = "microsoft/layoutlmv3-base"
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: list = None

    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = ["query", "value", "key"]


class LayoutLMv3Trainer:
    def __init__(self, config: ModelConfig, training_args: dict):
        self.config = config
        self.training_args = training_args

        # Load label mappings
        with open("../data/label_schema.json", "r") as f:
            label_schema = json.load(f)
            self.label2id = label_schema["label2id"]
            self.id2label = label_schema["id2label"]
            self.num_labels = len(self.label2id)

        # Load dataset
        self.dataset = load_from_disk("../data/formatted_dataset")
        logger.info(f"Loaded dataset: {self.dataset}")

        # Initialize model
        self.model = self._initialize_model()

        # Initialize trainer
        self.trainer = self._initialize_trainer()

    def _initialize_model(self):
        """Initialize LayoutLMv3 model with LoRA — sans kbit training"""
        logger.info(f"Loading model: {self.config.model_name}")

        model = LayoutLMv3ForTokenClassification.from_pretrained(
            self.config.model_name,
            num_labels=self.num_labels,
            label2id=self.label2id,
            id2label=self.id2label,
            ignore_mismatched_sizes=True
        )

        if self.config.use_lora:
            logger.info("Applying LoRA configuration")

            # CORRECTION : prepare_model_for_kbit_training supprimé
            # → il gelait tous les gradients sur CPU sans quantization

            peft_config = LoraConfig(
                task_type=TaskType.TOKEN_CLS,
                inference_mode=False,
                r=self.config.lora_r,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=self.config.lora_target_modules,
                bias="none"
            )

            model = get_peft_model(model, peft_config)
            model.print_trainable_parameters()

        return model

    def _initialize_trainer(self):
        """Initialize HuggingFace Trainer avec class weights"""

        seqeval = evaluate.load("seqeval")

        # CORRECTION : class weights pour corriger déséquilibre O vs entités
        # O représente ~95% des tokens → on le pénalise moins
        # Entités représentent ~5% des tokens → on les pénalise plus
        weights = torch.ones(self.num_labels)
        for label_str, label_id in self.label2id.items():
            
            if label_str == "O":
                weights[int(label_id)] = 0.05
            else:
                weights[int(label_id)] = 1.5

        logger.info(f"Class weights — O: 0.1, entités: 1.0")

        def compute_metrics(p):
            predictions, labels = p
            predictions = np.argmax(predictions, axis=2)

            true_predictions = [
                [self.id2label[str(p)] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [self.id2label[str(l)] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]

            results = seqeval.compute(
                predictions=true_predictions,
                references=true_labels
            )
            return {
                "precision": results["overall_precision"],
                "recall": results["overall_recall"],
                "f1": results["overall_f1"],
                "accuracy": results["overall_accuracy"],
            }

        # CORRECTION : fp16=False forcé (CPU uniquement)
        args = TrainingArguments(
            output_dir=self.training_args.get("output_dir", "../models/finetuned_lora"),
            num_train_epochs=self.training_args.get("num_train_epochs", 15),
            per_device_train_batch_size=self.training_args.get("per_device_train_batch_size", 4),
            per_device_eval_batch_size=self.training_args.get("per_device_eval_batch_size", 4),
            gradient_accumulation_steps=self.training_args.get("gradient_accumulation_steps", 4),
            learning_rate=self.training_args.get("learning_rate", 5e-5),
            weight_decay=self.training_args.get("weight_decay", 0.01),
            warmup_ratio=self.training_args.get("warmup_ratio", 0.1),
            logging_steps=self.training_args.get("logging_steps", 10),
            eval_steps=self.training_args.get("eval_steps", 30),
            save_steps=self.training_args.get("save_steps", 30),
            save_total_limit=self.training_args.get("save_total_limit", 2),
            load_best_model_at_end=self.training_args.get("load_best_model_at_end", True),
            metric_for_best_model=self.training_args.get("metric_for_best_model", "f1"),
            greater_is_better=self.training_args.get("greater_is_better", True),
            seed=self.training_args.get("seed", 42),
            fp16=False,
            dataloader_num_workers=self.training_args.get("dataloader_num_workers", 4),
            remove_unused_columns=self.training_args.get("remove_unused_columns", False),
            label_names=["labels"],
            eval_strategy="steps",
            save_strategy="steps",
            report_to="none",
        )

        # CORRECTION : WeightedTrainer remplace Trainer standard
        # compute_loss redéfini pour appliquer les class weights
        class WeightedTrainer(Trainer):
            def __init__(self, class_weights, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.class_weights = class_weights

            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                logits = outputs.logits

                # Déplacer les weights sur le bon device
                weights = self.class_weights.to(logits.device)

                loss_fct = torch.nn.CrossEntropyLoss(weight=weights)
                loss = loss_fct(
                    logits.view(-1, model.config.num_labels),
                    labels.view(-1)
                )

                return (loss, outputs) if return_outputs else loss

        callbacks = []
        if self.training_args.get("early_stopping", True):
            callbacks.append(EarlyStoppingCallback(
                early_stopping_patience=3,
                early_stopping_threshold=0.01
            ))

        trainer = WeightedTrainer(
            class_weights=weights,
            model=self.model,
            args=args,
            train_dataset=self.dataset["train"],
            eval_dataset=self.dataset["validation"],
            compute_metrics=compute_metrics,
            callbacks=callbacks,
        )

        return trainer

    def train(self):
        """Start training"""
        logger.info("Starting training...")

        train_result = self.trainer.train()

        # Save final model
        self.trainer.save_model()
        self.trainer.save_state()

        # Log metrics
        metrics = train_result.metrics
        self.trainer.log_metrics("train", metrics)
        self.trainer.save_metrics("train", metrics)

        # Evaluate
        logger.info("Evaluating...")
        eval_metrics = self.trainer.evaluate()
        self.trainer.log_metrics("eval", eval_metrics)
        self.trainer.save_metrics("eval", eval_metrics)

        return metrics, eval_metrics

    def save_model(self, output_path: str = None):
        """Save the trained model"""
        if output_path is None:
            output_path = self.training_args.get("output_dir", "../models/finetuned_lora")

        self.model.save_pretrained(output_path)

        processor = LayoutLMv3Processor.from_pretrained(self.config.model_name)
        processor.save_pretrained(output_path)

        config = {
            "model_config": self.config.__dict__,
            "training_args": self.training_args,
            "label2id": self.label2id,
            "id2label": self.id2label
        }

        with open(os.path.join(output_path, "training_config.json"), "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Model saved to {output_path}")


if __name__ == "__main__":
    # Load training arguments
    with open("../configs/training_args.json", "r") as f:
        training_args = json.load(f)

    # Model config
    model_config = ModelConfig(
        model_name="microsoft/layoutlmv3-base",
        use_lora=True,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.1
    )

    # Initialize trainer
    trainer = LayoutLMv3Trainer(model_config, training_args)

    # Train
    train_metrics, eval_metrics = trainer.train()

    # Save model
    trainer.save_model()

    # Print results
    logger.info("Training completed!")
    logger.info(f"Train metrics: {train_metrics}")
    logger.info(f"Eval metrics: {eval_metrics}")