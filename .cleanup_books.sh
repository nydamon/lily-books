#!/bin/bash
# Clean up old test book directories
cd "/Users/damondecrescenzo/Lily books/books" || exit 1

echo "Cleaning up test book directories..."
echo "Keeping only: langfuse-test (latest validated test)"
echo ""

# List what we're removing
echo "Removing directories..."
ls -1 | grep -v "langfuse-test" | while read dir; do
    echo "  - $dir"
    rm -rf "$dir"
done

echo ""
echo "✅ Cleanup complete"
echo ""
echo "Remaining books:"
ls -1



