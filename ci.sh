#!/bin/bash
set -e  # Exit on error

OS=$(uname -s)
echo "Running tests on $OS..."

# Run pytest
if [ -d "tests" ]; then
    pytest tests -v
fi

# Run examples based on OS
if [ "$OS" = "Darwin" ]; then
    # Mac: only run simulation
    echo "Mac detected, running simulation only..."
    python examples/scripts/run_all_examples.py --runtime host_build_graph -p a2a3sim -v 0
else
    # Linux: run all platforms
    echo "Linux detected, running all platforms..."
    python examples/scripts/run_all_examples.py --runtime host_build_graph -p a2a3 -d 5 -v 0
    python examples/scripts/run_all_examples.py --runtime host_build_graph -p a2a3sim -v 0
fi

echo "All tests passed!"
