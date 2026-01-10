#!/bin/bash
# RISC-V VDSO Time Cache Automated Test Runner
#
# This script automates the execution of all VDSO cache tests
# and generates comprehensive reports.
#
# Usage: ./run_tests.sh [OPTIONS]
#
# Options:
#   --quick        Quick test (skip stress tests)
#   --full         Full test suite
#   --performance  Performance tests only
#   --accuracy     Accuracy tests only
#   --report       Generate HTML report
#   --json         Generate JSON report
#   --clean        Clean test binaries
#   --help         Show this help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_DIR="$(dirname "$0")"
BUILD_DIR="$TEST_DIR/build"
REPORT_DIR="$TEST_DIR/reports"
TEST_PROGRAM="$BUILD_DIR/vdso_cache_test"
PERF_PROGRAM="$BUILD_DIR/vdso_perf_benchmark"

# Test results
TESTS_PASS=0
TESTS_FAIL=0
TEST_START_TIME=$(date +%s)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo ""
    echo "=============================================="
    echo "  $1"
    echo "=============================================="
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warning "Not running as root. Some tests may fail."
        log_warning "Consider running with sudo for accurate results."
        return 1
    fi
    return 0
}

check_kernel_config() {
    print_header "Checking Kernel Configuration"

    if [ ! -f /proc/config.gz ]; then
        log_warning "/proc/config.gz not found. Cannot verify kernel config."
        log_warning "Ensure kernel was built with CONFIG_IKCONFIG_PROC=y"
        return 1
    fi

    local cache_enabled=$(zcat /proc/config.gz 2>/dev/null | grep CONFIG_RISCV_VDSO_TIME_CACHE= || echo "not found")

    if echo "$cache_enabled" | grep -q "y"; then
        log_success "VDSO Time Cache: ENABLED"
    else
        log_warning "VDSO Time Cache: NOT ENABLED"
        log_warning "Performance tests may not show expected improvements."
    fi

    local generic_gettime=$(zcat /proc/config.gz 2>/dev/null | grep CONFIG_GENERIC_GETTIMEOFDAY= || echo "not found")
    if echo "$generic_gettime" | grep -q "y"; then
        log_success "Generic VDSO: ENABLED"
    else
        log_error "Generic VDSO: NOT ENABLED"
        return 1
    fi

    return 0
}

check_vdso() {
    print_header "Checking VDSO Availability"

    if ldd /bin/ls 2>/dev/null | grep -q vdso; then
        log_success "VDSO is loaded in processes"
    else
        log_warning "Cannot verify VDSO loading"
    fi

    if [ -f /proc/self/maps ]; then
        local vdso_count=$(grep vdso /proc/self/maps | wc -l)
        log_success "VDSO mappings in current process: $vdso_count"
    fi
}

build_tests() {
    print_header "Building Test Programs"

    mkdir -p "$BUILD_DIR"
    cd "$TEST_DIR"

    # Check if rebuild is needed
    if [ -f "$TEST_PROGRAM" ] && [ "$TEST_PROGRAM" -nt "vdso_cache_test.c" ]; then
        log_info "Test binaries already up to date"
        return 0
    fi

    log_info "Compiling test programs..."

    # Build main test program
    gcc -O2 -g -o "$TEST_PROGRAM" vdso_cache_test.c -lrt -lpthread
    if [ $? -eq 0 ]; then
        log_success "Built: vdso_cache_test"
    else
        log_error "Failed to build vdso_cache_test"
        return 1
    fi

    # Build performance benchmark
    if [ -f "vdso_perf_benchmark.c" ]; then
        gcc -O2 -g -o "$PERF_PROGRAM" vdso_perf_benchmark.c -lrt
        if [ $? -eq 0 ]; then
            log_success "Built: vdso_perf_benchmark"
        fi
    fi

    return 0
}

run_quick_tests() {
    print_header "Running Quick Tests"
    check_root || true

    if [ ! -f "$TEST_PROGRAM" ]; then
        log_error "Test program not found. Building..."
        build_tests || return 1
    fi

    "$TEST_PROGRAM" --quick
    return $?
}

run_full_tests() {
    print_header "Running Full Test Suite"
    check_root || true

    if [ ! -f "$TEST_PROGRAM" ]; then
        log_error "Test program not found. Building..."
        build_tests || return 1
    fi

    "$TEST_PROGRAM"
    return $?
}

run_performance_tests() {
    print_header "Running Performance Tests"
    check_root || true

    if [ ! -f "$PERF_PROGRAM" ]; then
        log_error "Performance benchmark not found. Building..."
        build_tests || return 1
    fi

    "$PERF_PROGRAM"
    return $?
}

run_accuracy_tests() {
    print_header "Running Accuracy Tests"
    check_root || true

    if [ ! -f "$TEST_PROGRAM" ]; then
        log_error "Test program not found. Building..."
        build_tests || return 1
    fi

    "$TEST_PROGRAM" --skip-perf --skip-stress
    return $?
}

generate_html_report() {
    print_header "Generating HTML Report"

    mkdir -p "$REPORT_DIR"
    local report_file="$REPORT_DIR/test_report_$(date +%Y%m%d_%H%M%S).html"

    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RISC-V VDSO Time Cache Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .pass { color: #27ae60; font-weight: bold; }
        .fail { color: #e74c3c; font-weight: bold; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #ecf0f1; border-radius: 3px; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>RISC-V VDSO Time Cache Test Report</h1>
        <p class="timestamp">Generated: $(date)</p>
    </div>

    <div class="section">
        <h2>Test Environment</h2>
        <pre>
Kernel: $(uname -r)
Architecture: $(uname -m)
CPU: $(lscpu | grep "Model name" | head -1 || echo "Unknown")
        </pre>
    </div>

    <div class="section">
        <h2>Test Summary</h2>
        <div class="metric">Total Tests: $((TESTS_PASS + TESTS_FAIL))</div>
        <div class="metric"><span class="pass">Passed: $TESTS_PASS</span></div>
        <div class="metric"><span class="fail">Failed: $TESTS_FAIL</span></div>
    </div>

    <div class="section">
        <h2>Configuration</h2>
        <pre>
$(check_kernel_config 2>&1 | sed 's/\x1b\[[0-9;]*m//g')
        </pre>
    </div>

    <div class="section">
        <h2>Performance Results</h2>
        <pre>
$(run_performance_tests 2>&1 | sed 's/\x1b\[[0-9;]*m//g')
        </pre>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            <li>Compare results with and without CONFIG_RISCV_VDSO_TIME_CACHE</li>
            <li>Run tests multiple times to get consistent measurements</li>
            <li>Check dmesg for any VDSO-related errors</li>
        </ul>
    </div>
</body>
</html>
EOF

    log_success "Report generated: $report_file"
}

generate_json_report() {
    print_header "Generating JSON Report"

    mkdir -p "$REPORT_DIR"
    local report_file="$REPORT_DIR/test_results_$(date +%Y%m%d_%H%M%S).json"

    cat > "$report_file" <<EOF
{
    "test_suite": "RISC-V VDSO Time Cache",
    "timestamp": "$(date -Iseconds)",
    "kernel_version": "$(uname -r)",
    "architecture": "$(uname -m)",
    "tests": {
        "total": $((TESTS_PASS + TESTS_FAIL)),
        "passed": $TESTS_PASS,
        "failed": $TESTS_FAIL
    },
    "environment": {
        "cpu_freq_mhz": $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | awk '{print $1/1000}' || echo "null")
    }
}
EOF

    log_success "JSON report generated: $report_file"
}

clean() {
    print_header "Cleaning Test Artifacts"

    rm -rf "$BUILD_DIR"
    rm -rf "$REPORT_DIR"

    log_success "Clean complete"
}

show_help() {
    cat <<HELP
Usage: $0 [OPTIONS]

Options:
  --quick        Run quick tests (skip stress tests)
  --full         Run full test suite (default)
  --performance  Run performance tests only
  --accuracy     Run accuracy tests only
  --report       Generate HTML report
  --json         Generate JSON report
  --clean        Clean test binaries and reports
  --help         Show this help message

Examples:
  $0                      # Run full test suite
  $0 --quick              # Run quick tests
  $0 --performance        # Run only performance tests
  $0 --report             # Generate HTML report after tests

Notes:
  - Some tests require root privileges for accurate results
  - For best results, run on an idle system
  - Compare results with CONFIG_RISCV_VDSO_TIME_CACHE enabled/disabled
HELP
}

# Main script
main() {
    local mode="full"
    local gen_report=false
    local gen_json=false

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --quick)
                mode="quick"
                shift
                ;;
            --full)
                mode="full"
                shift
                ;;
            --performance)
                mode="performance"
                shift
                ;;
            --accuracy)
                mode="accuracy"
                shift
                ;;
            --report)
                gen_report=true
                shift
                ;;
            --json)
                gen_json=true
                shift
                ;;
            --clean)
                clean
                exit 0
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Run pre-flight checks
    print_header "VDSO Cache Test Suite"
    log_info "Test mode: $mode"
    log_info "Start time: $(date)"

    check_kernel_config
    check_vdso
    build_tests

    # Run tests based on mode
    case "$mode" in
        quick)
            run_quick_tests || true
            ;;
        performance)
            run_performance_tests || true
            ;;
        accuracy)
            run_accuracy_tests || true
            ;;
        full)
            run_full_tests || true
            ;;
    esac

    # Capture exit code
    local exit_code=$?

    # Generate reports if requested
    if [ "$gen_report" = true ]; then
        generate_html_report
    fi

    if [ "$gen_json" = true ]; then
        generate_json_report
    fi

    # Final summary
    print_header "Test Run Complete"
    log_info "End time: $(date)"
    log_info "Duration: $(($(date +%s) - TEST_START_TIME)) seconds"

    if [ $exit_code -eq 0 ]; then
        log_success "All tests completed successfully!"
    else
        log_error "Some tests failed. Check output above."
    fi

    exit $exit_code
}

main "$@"
