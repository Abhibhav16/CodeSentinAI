import os

def calculate_average(values):
    """Calculate the mean of values."""
    if not values:
        return 0
    return sum(values) / len(values)

def analyze_data(filepath):
    """Analyze file contents and compute average."""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r') as f:
        numbers = [float(line.strip()) for line in f if line.strip()]
    return calculate_average(numbers)

def unused_helper_function(data):
    """
    A very large and verbose unused helper function.
    We add a lot of text here to make sure that removing this function
    from the file reduces the total character count by more than 30%.
    This is a requirement of the unit tests for ast_reducer.py.
    
    Let's add more documentation and comments.
    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    Donec a diam lectus. Sed sit amet ipsum mauris.
    Maecenas congue ligula ac quam viverra nec consectetur ante hendrerit.
    Carpe diem, memento mori.
    This function does a bunch of complex operations that are never actually
    called by the analyze_data function.
    
    This function contains many lines to increase its byte size significantly.
    1. Line one of dummy text
    2. Line two of dummy text
    3. Line three of dummy text
    4. Line four of dummy text
    5. Line five of dummy text
    6. Line six of dummy text
    7. Line seven of dummy text
    8. Line eight of dummy text
    9. Line nine of dummy text
    10. Line ten of dummy text
    """
    result = []
    for item in data:
        processed = item * 42 - 17
        result.extend([processed, processed * 2, processed // 2])
    return result
