"""CSV Handler for status queue management."""

import csv
import os
from dataclasses import dataclass
from typing import List, Optional

HEADER_IMAGE = "Image Name"
HEADER_CAPTION = "Caption Description"
HEADER_STATUS = "Uploaded Status"

REQUIRED_HEADERS = [HEADER_IMAGE, HEADER_CAPTION]
FULL_HEADERS = [HEADER_IMAGE, HEADER_CAPTION, HEADER_STATUS]


@dataclass
class QueueItem:
    image_name: str
    caption: str
    status: str
    row_index: int  # To track which row to update


class CsvHandler:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._ensure_status_column() 
        
    def _ensure_status_column(self) -> None:
        """Ensure the CSV has the required columns, adding 'Uploaded Status' if missing."""
        if not os.path.exists(self.csv_path):
            # Create new file with headers if it doesn't exist
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=FULL_HEADERS)
                writer.writeheader()
            return

        rows = []
        fieldnames = []
        needs_update = False

        # Read fully into memory to avoid read/write conflict
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return # Empty file
            
            fieldnames = list(reader.fieldnames)
            
            # Check for header existence
            has_status = any(h.lower() == HEADER_STATUS.lower() for h in fieldnames)
            
            if not has_status:
                needs_update = True
                fieldnames.append(HEADER_STATUS)

            for row in reader:
                # Initialize status if column missing or cell empty
                # Note: DictReader won't have the new key if it wasn't in fieldnames
                # We need to manually ensure it.
                if HEADER_STATUS not in row and not has_status:
                    row[HEADER_STATUS] = "No"
                elif HEADER_STATUS in row and not row[HEADER_STATUS]:
                     row[HEADER_STATUS] = "No" # Fill empty cells
                rows.append(row)

        if needs_update:
             with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    if HEADER_STATUS not in row:
                        row[HEADER_STATUS] = "No"
                    writer.writerow(row)

    def read_queue(self, filter_status: Optional[str] = None) -> List[QueueItem]:
        """Read the queue, optionally filtering by current status ('No')."""
        items = []
        if not os.path.exists(self.csv_path):
            return items

        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Handle potential missing columns gracefully or skip
                image = row.get(HEADER_IMAGE, "").strip()
                caption = row.get(HEADER_CAPTION, "").strip()
                status = row.get(HEADER_STATUS, "No").strip()

                if not image:
                    continue

                if filter_status and status.lower() != filter_status.lower():
                    continue
                
                items.append(QueueItem(image, caption, status, i))
        return items

    def update_status(self, row_index: int, new_status: str) -> None:
        """Update the status of a specific row by index."""
        # Read all rows
        rows = []
        fieldnames = []
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        if 0 <= row_index < len(rows):
            rows[row_index][HEADER_STATUS] = new_status

        # Write back
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def reset_all_statuses(self) -> None:
        """Reset all 'Uploaded Status' entries to 'No'."""
        if not os.path.exists(self.csv_path):
            return

        rows = []
        fieldnames = []
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                row[HEADER_STATUS] = "No"
                rows.append(row)

        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def validate(self) -> str:
        """Check if CSV is valid. Returns error message or empty string."""
        if not os.path.exists(self.csv_path):
            return f"File not found: {self.csv_path}"
        
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return "CSV file is empty or missing headers."
                
                missing = [h for h in REQUIRED_HEADERS if h not in reader.fieldnames]
                if missing:
                    return f"Missing columns: {', '.join(missing)}"
        except Exception as e:
            return f"Error reading CSV: {str(e)}"
            
        return ""
