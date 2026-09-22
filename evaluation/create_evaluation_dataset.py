import pandas as pd
import os
columns = [
    "id",
    "query",
    "label"
]
current_folder = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_folder, "test.csv")
df = pd.DataFrame(columns=columns)
df.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig"
)
print("đã tạo test.csv")