# Thai ID Extraction Logic

This document describes the logic used to identify and extract the **Payee's Thai National/Tax ID** from 50 Twi (Withholding Tax Certificate) PDF forms.

## 1. Regex Pattern
We use a flexible regex to handle various formatting styles found in documents, including those with spaces or dashes between digits.

```python
# Flexible regex allowing dashes and spaces anywhere between digits
# Matches 13 digits with arbitrary spacing/dashing
# Example matches: "1-2345-67890-12-3", "1 2345 67890 12 3", "0 9 9 4..."
THAI_ID_REGEX = r"\b\d(?:\s*[-]?\s*\d){12}\b"
```

## 2. Selection Strategy (Payee vs Payer)
A standard 50 Twi form contains at least two tax IDs:
1.  **Payer's ID (ผู้มีหน้าที่หักภาษี)**: Located at the top of the form.
2.  **Payee's ID (ผู้ถูกหักภาษี)**: Located below the Payer's ID.

To ensure we extract the **Payee's ID** (Target Person), the system applies the following logic:

### Step 1: Find all valid ID candidates
The system scans the entire text of the page and collects all sequences matching the regex.
- All matches are cleaned (removing spaces and dashes).
- Only matches with exactly 13 digits are kept.

### Step 2: Search for Keyword "ผู้ถูกหักภาษี"
The system searches for the position of the phrase `ผู้ถูกหักภาษี` (Payee).
- If found, it filters for the first ID candidate that appears **after** this keyword.

### Step 3: Fallback by Position
If the keyword is not found (e.g., due to extraction issues):
- The system checks if there are at least 2 IDs found.
- It assumes the **second ID** is the Payee's ID (based on standard form layout where Payer is first).

### Step 4: Default
If only one ID is found, distinct or otherwise, it defaults to returning that ID.
