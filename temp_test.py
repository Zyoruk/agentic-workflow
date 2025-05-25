def test1(data):
    """This is similar to what's in safety_checks.py."""
    items = ["a", "b", "c"]

    # Check if data contains any items
    for item in items:
        if item in data:
            return {
                "is_match": True,
                "item": item,
            }

    # No match found
    return {"is_match": False}

# Fix 1: Move the return outside the loop
def test2(data):
    """First potential fix."""
    items = ["a", "b", "c"]

    for item in items:
        if item in data:
            return {
                "is_match": True,
                "item": item,
            }
    return {"is_match": False}

# Fix 2: Use a variable to track matches
def test3(data):
    """Second potential fix."""
    items = ["a", "b", "c"]
    found_item = None

    for item in items:
        if item in data:
            found_item = item
            break

    if found_item:
        return {
            "is_match": True,
            "item": found_item,
        }
    return {"is_match": False}

if __name__ == "__main__":
    print("Running tests...")
    print(test1("abc"))  # Should match
    print(test1("xyz"))  # Should not match
    print(test2("abc"))  # Should match
    print(test2("xyz"))  # Should not match
    print(test3("abc"))  # Should match
    print(test3("xyz"))  # Should not match
