import re

def clean_encoding_artifacts(text):
    """
    Remove encoding artifacts like  (non-breaking space) that appear before special characters.
    Common patterns: Â°, Â£, Â©, etc.

    Args:
        text (str): Input text with encoding artifacts

    Returns:
        str: Cleaned text without encoding artifacts
    """
    # Remove  before common special characters
    cleaned = re.sub(r'Â°', '°', text)  # Degree symbol
    cleaned = re.sub(r'Â£', '£', cleaned)  # Pound sign
    cleaned = re.sub(r'Â©', '©', cleaned)  # Copyright
    cleaned = re.sub(r'Â®', '®', cleaned)  # Registered trademark
    cleaned = re.sub(r'Â', '', cleaned)  # Any remaining


    # Also clean up other common encoding issues
    cleaned = re.sub(r'â€™', "'", cleaned)  # Smart apostrophe
    cleaned = re.sub(r'â€œ', '"', cleaned)  # Smart quote left
    cleaned = re.sub(r'â€', '"', cleaned)  # Smart quote right
    cleaned = re.sub(r'â€"', '—', cleaned)  # Em dash
    cleaned = re.sub(r'â€"', '–', cleaned)  # En dash

    return cleaned

def clean_asterisks(text):
    """
    Remove ** formatting from headings and text, and specifically remove Demographics heading.

    Args:
        text (str): Input text with ** formatting

    Returns:
        str: Cleaned text without ** formatting and without Demographics heading
    """
    # Remove ** from around headings (e.g., **Demographics:** -> Demographics:)
    cleaned = re.sub(r'\*\*([^*]+?):\*\*', r'\1:', text)

    # Remove any remaining ** pairs
    cleaned = re.sub(r'\*\*([^*]+?)\*\*', r'\1', cleaned)

    # Remove any stray asterisks
    cleaned = cleaned.replace('**', '')

    # Remove "Demographics:" heading (with or without line breaks before/after)
    cleaned = re.sub(r'Demographics:\s*\n?', '', cleaned)
    cleaned = re.sub(r'\n+Demographics:\s*\n?', '\n', cleaned)

    return cleaned


def clean_file(input_file, output_file=None):
    """
    Clean asterisks from a file.

    Args:
        input_file (str): Path to input file
        output_file (str): Path to output file (optional, defaults to input_file)
    """
    if output_file is None:
        output_file = input_file

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Apply all cleaning functions
    cleaned_content = clean_encoding_artifacts(content)
    cleaned_content = clean_asterisks(cleaned_content)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

    print(f"Cleaned file saved to: {output_file}")
