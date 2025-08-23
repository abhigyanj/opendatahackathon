enc = "cp932"

with open("data.csv", encoding=enc) as f:
    text = f.read()

print(f"Decoded with {enc}")
print(text)
