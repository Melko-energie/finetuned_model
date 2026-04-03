# Design System Strategy: The Architectural Ledger

## 1. Overview & Creative North Star: "The Architectural Ledger"
This design system moves away from the "toy-like" defaults of standard data apps to embrace a "High-End Editorial" aesthetic tailored for the BTP (Construction) sector. Our North Star is **The Architectural Ledger**: a visual philosophy that treats data with the same precision, weight, and structural integrity as a blueprinted floor plan. 

We break the "template" look by utilizing **intentional asymmetry** and **tonal layering**. Instead of boxes inside boxes, we use expansive white space and shifting surface values to guide the eye. The UI should feel like a premium, physical workspace—composed of stacked sheets of vellum and frosted glass—where the complexity of construction invoices is met with the clarity of professional drafting.

---

## 2. Colors & Surface Philosophy
The palette is rooted in the "Melko" blues and professional grays, but applied through a lens of depth rather than flat fills.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning. Boundaries must be defined solely through background color shifts. 
*   Use `surface_container_low` for the main background.
*   Use `surface_container_lowest` (Pure White) for primary data cards.
*   Use `surface_container_high` for nested utility panels.

### Surface Hierarchy & Nesting
Treat the UI as physical layers.
*   **Base:** `background` (#f7f9fb)
*   **Sidebar/Navigation:** `surface_container` (#eceef0)
*   **Primary Content Cards:** `surface_container_lowest` (#ffffff)
*   **Active Overlays:** `surface_bright` with a backdrop blur of 12px.

### The "Glass & Gradient" Rule
To elevate the header and primary actions:
*   **Header Gradient:** Linear transition from `primary` (#003d9b) to `primary_container` (#0052cc) at a 135-degree angle.
*   **Glassmorphism:** For "Floating" document previews, use `surface_container_lowest` at 80% opacity with a `backdrop-filter: blur(16px)`.

### Functional Status Indicators
*   **Inconsistency:** `tertiary_container` (#805000) text on `tertiary_fixed` background.
*   **Missing Data:** `error` (#ba1a1a) text on `error_container` (#ffdad6).
*   **Credit Notes (Avoirs):** A bespoke "Caution" state using the `on_tertiary_fixed_variant` (#653e00) to ensure readability on yellow-tinted backgrounds.

---

## 3. Typography: Editorial Precision
We utilize two distinct sans-serif families to balance character with utility.

*   **Display & Headlines (Manrope):** Chosen for its geometric, architectural proportions. Used for page titles and high-level metrics.
    *   *Display-MD:* 2.75rem. Use for total invoice amounts or major dashboard headings.
*   **Body & Data (Inter):** The workhorse for invoice extraction. Inter’s tall x-height ensures that small technical strings (VAT numbers, IBANs) remain legible.
    *   *Title-SM:* 1rem (Inter Medium). Use for table headers.
    *   *Label-MD:* 0.75rem (Inter Bold, All Caps, Letter Spacing +5%). Use for metadata tags and document status.

---

## 4. Elevation & Depth
Depth is a functional tool, not a decorative one. 

*   **The Layering Principle:** Avoid shadows for static elements. A `surface_container_lowest` card placed on a `surface_container_low` background provides enough contrast for the eye to perceive a 2mm "lift."
*   **Ambient Shadows:** Use only for floating modals or active "drag-and-drop" states. 
    *   *Value:* `0px 20px 40px rgba(25, 28, 30, 0.06)`. 
    *   The shadow is never black; it is a tinted version of `on_surface`.
*   **The "Ghost Border" Fallback:** If a divider is required for extreme data density, use the `outline_variant` (#c3c6d6) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Tabbed Navigation
*   **Style:** No "folder tab" shapes. Use "Underline" style with a 3px thick `primary` bar for the active state. 
*   **Inactive:** `on_surface_variant` text with no background.

### Stylized Upload Zone
*   **Visual:** A large area using `surface_container_high` with a dashed `outline_variant` (20% opacity). 
*   **Interaction:** Upon hover, the background transitions to `primary_fixed` with a 0.3s ease. Use a `primary` icon to draw focus.

### Data Tables
*   **Constraint:** No vertical or horizontal lines. 
*   **Row Stripping:** Use `surface_container_low` for even rows. 
*   **Header:** `on_surface_variant` in `label-md` (Inter Bold/Caps).

### Buttons
*   **Primary:** `primary` (#003d9b) background. Corner radius: `md` (0.375rem).
*   **Secondary:** `secondary_container` (#d0e1fb) background. No border.
*   **Tertiary (Ghost):** No background. Text color `primary`. Use for "Cancel" or "Go Back."

### Specialized Invoice Components
*   **Confidence Score Chips:** Small pills using `tertiary_fixed` (#ffddb8) to denote AI confidence levels.
*   **Document Preview Card:** A "Sheet" metaphor using `surface_container_lowest` with a very soft ambient shadow to simulate a piece of paper on a desk.

---

## 6. Do's and Don'ts

### Do
*   **DO** use whitespace as a separator. If you think you need a line, try adding 16px of padding instead.
*   **DO** use `manrope` for numbers. Its geometric nature makes financial figures feel more authoritative.
*   **DO** use high-contrast text (`on_surface`) for primary data and lower-contrast (`on_surface_variant`) for labels.

### Don't
*   **DON'T** use pure black (#000000) for text or shadows. Use `on_surface` (#191c1e).
*   **DON'T** use 100% opaque borders. They clutter the "Architectural Ledger" and break the flow of information.
*   **DON'T** use vibrant, saturated orange/red/yellow as background fills. Keep them as "Container" colors (light tints) with dark text to maintain the professional, premium tone.