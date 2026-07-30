# Utility helper functions
def format_bytes(size_bytes: int) -> str:
    """Formats bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{round(size_bytes, 2)} {size_name[i]}"
