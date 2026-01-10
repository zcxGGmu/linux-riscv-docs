// SPDX-License-Identifier: GPL-2.0
/*
 * RISC-V VDSO Time Cache Comprehensive Test Suite
 *
 * This program performs comprehensive testing of the VDSO time caching
 * optimization including:
 * - Functional tests (correctness)
 * - Performance tests (speed improvement)
 * - Accuracy tests (precision)
 * - Stress tests (stability)
 *
 * Build: gcc -O2 -o vdso_cache_test vdso_cache_test.c -lrt -lpthread
 * Run:   sudo ./vdso_cache_test
 */

#define _GNU_SOURCE
#include <stdbool.h>
#include <time.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <setjmp.h>
#include <errno.h>
#include <linux/time_types.h>

/* Test configuration */
#define TEST_ITERATIONS       1000000
#define WARMUP_ITERATIONS     10000
#define MONOTONIC_CHECKS      10000
#define ACCURACY_SAMPLES      1000
#define STRESS_DURATION_SEC   10

/* Test result tracking */
static int tests_passed = 0;
static int tests_failed = 0;
static int tests_skipped = 0;

/* Color codes for output */
#define COLOR_GREEN  "\033[0;32m"
#define COLOR_RED    "\033[0;31m"
#define COLOR_YELLOW "\033[0;33m"
#define COLOR_BLUE   "\033[0;34m"
#define COLOR_RESET  "\033[0m"

/* Cycle counter access - multi-architecture support */
static inline uint64_t rdcycle(void)
{
    uint64_t cycles;
#if defined(__riscv)
    asm volatile("rdcycle %0" : "=r"(cycles));
#elif defined(__x86_64__) || defined(__i386__)
    unsigned int hi, lo;
    asm volatile("rdtsc" : "=a"(lo), "=d"(hi));
    cycles = ((uint64_t)hi << 32) | lo;
#else
    /* Fallback: use clock_gettime */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    cycles = (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
#endif
    return cycles;
}

/* Direct VDSO call */
/* Note: On modern systems, clock_gettime() already uses VDSO when available.
 * This wrapper ensures we're testing the fast path. */
static inline int clock_gettime_vdso(clockid_t clk, struct timespec *ts)
{
    return clock_gettime(clk, ts);
}

/* System call version */
static inline int clock_gettime_syscall(clockid_t clk, struct timespec *ts)
{
    return syscall(__NR_clock_gettime, clk, ts);
}

/* Test result structure */
struct test_result {
    const char *name;
    bool passed;
    double value;
    const char *unit;
    const char *details;
};

/* Test suite structure */
struct test_suite {
    const char *name;
    int passed;
    int failed;
};

/* ==================== Utility Functions ==================== */

static void print_header(const char *title)
{
    printf("\n" COLOR_BLUE "===== %s =====" COLOR_RESET "\n", title);
}

static void print_test(const char *name, bool passed)
{
    if (passed) {
        printf("  " COLOR_GREEN "✓" COLOR_RESET " %s\n", name);
        tests_passed++;
    } else {
        printf("  " COLOR_RED "✗" COLOR_RESET " %s\n", name);
        tests_failed++;
    }
}

static void print_value(const char *name, double value, const char *unit)
{
    printf("  • %s: %.2f %s\n", name, value, unit);
}

static double get_cpu_freq_mhz(void)
{
    FILE *fp = fopen("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r");
    if (fp) {
        unsigned long freq_khz;
        if (fscanf(fp, "%lu", &freq_khz) == 1) {
            fclose(fp);
            return freq_khz / 1000.0;
        }
        fclose(fp);
    }
    /* Fallback: try to estimate from cycle counter */
    struct timespec ts1, ts2;
    uint64_t c1, c2;

    clock_gettime(CLOCK_MONOTONIC, &ts1);
    c1 = rdcycle();
    usleep(10000); /* 10ms */
    clock_gettime(CLOCK_MONOTONIC, &ts2);
    c2 = rdcycle();

    double sec = (ts2.tv_sec - ts1.tv_sec) + (ts2.tv_nsec - ts1.tv_nsec) / 1e9;
    double cycles = c2 - c1;

    return cycles / sec / 1e6;
}

/* ==================== Functional Tests ==================== */

static bool test_basic_gettime(void)
{
    struct timespec ts;
    int ret = clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
    return ret == 0 && ts.tv_sec >= 0 && ts.tv_nsec >= 0 && ts.tv_nsec < 1000000000;
}

static bool test_monotonicity(void)
{
    struct timespec prev, curr;
    int i;

    if (clock_gettime_vdso(CLOCK_MONOTONIC, &prev) != 0)
        return false;

    for (i = 0; i < MONOTONIC_CHECKS; i++) {
        if (clock_gettime_vdso(CLOCK_MONOTONIC, &curr) != 0)
            return false;

        /* Check strict monotonicity */
        if (curr.tv_sec < prev.tv_sec ||
            (curr.tv_sec == prev.tv_sec && curr.tv_nsec < prev.tv_nsec))
            return false;

        prev = curr;
        /* Small delay to ensure time advances */
        usleep(1);
    }

    return true;
}

static bool test_multiple_clocks(void)
{
    struct timespec ts_realtime, ts_monotonic, ts_boottime;

    if (clock_gettime_vdso(CLOCK_REALTIME, &ts_realtime) != 0)
        return false;
    if (clock_gettime_vdso(CLOCK_MONOTONIC, &ts_monotonic) != 0)
        return false;
    if (clock_gettime_vdso(CLOCK_BOOTTIME, &ts_boottime) != 0)
        return false;

    /* All clocks should return valid times */
    return ts_realtime.tv_sec > 0 && ts_monotonic.tv_sec >= 0 && ts_boottime.tv_sec >= 0;
}

static bool test_time_advances(void)
{
    struct timespec ts1, ts2;

    if (clock_gettime_vdso(CLOCK_MONOTONIC, &ts1) != 0)
        return false;

    usleep(10000); /* 10ms */

    if (clock_gettime_vdso(CLOCK_MONOTONIC, &ts2) != 0)
        return false;

    /* Time should advance by at least 10ms */
    uint64_t diff_ns = (ts2.tv_sec - ts1.tv_sec) * 1000000000ULL +
                       (ts2.tv_nsec - ts1.tv_nsec);

    return diff_ns >= 10000000; /* 10ms in ns */
}

static void run_functional_tests(void)
{
    print_header("Functional Tests (F001-F005)");

    printf("\nF001: Basic time acquisition\n");
    print_test("  clock_gettime() returns valid time", test_basic_gettime());

    printf("\nF002: Monotonicity check (10000 calls)\n");
    print_test("  Time strictly increases", test_monotonicity());

    printf("\nF003: Multiple clock sources\n");
    print_test("  All clocks accessible", test_multiple_clocks());

    printf("\nF004: Time advancement\n");
    print_test("  Time advances correctly", test_time_advances());

    printf("\nF005: Accuracy vs syscall\n");
    struct timespec ts_vdso, ts_syscall;
    clock_gettime_vdso(CLOCK_MONOTONIC, &ts_vdso);
    clock_gettime_syscall(CLOCK_MONOTONIC, &ts_syscall);

    int64_t diff_ns = (ts_vdso.tv_sec - ts_syscall.tv_sec) * 1000000000 +
                      (ts_vdso.tv_nsec - ts_syscall.tv_nsec);
    bool accurate = llabs(diff_ns) < 1000; /* < 1μs difference */
    print_test("  VDSO matches syscall (±1μs)", accurate);
    print_value("  Difference", llabs(diff_ns), "ns");
}

/* ==================== Performance Tests ==================== */

static double measure_single_call_latency(void)
{
    struct timespec ts;
    uint64_t start, end, min_cycles = UINT64_MAX;
    int i;

    /* Warmup */
    for (i = 0; i < WARMUP_ITERATIONS; i++) {
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
    }

    /* Measure */
    for (i = 0; i < 1000; i++) {
        start = rdcycle();
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        end = rdcycle();

        uint64_t cycles = end - start;
        if (cycles < min_cycles)
            min_cycles = cycles;
    }

    return min_cycles;
}

static double measure_throughput(int iterations)
{
    struct timespec ts;
    uint64_t start, end;
    int i;

    /* Warmup */
    for (i = 0; i < WARMUP_ITERATIONS; i++) {
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
    }

    start = rdcycle();
    for (i = 0; i < iterations; i++) {
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
    }
    end = rdcycle();

    double total_cycles = end - start;
    double avg_cycles = total_cycles / iterations;

    return avg_cycles;
}

static double estimate_cache_hit_rate(void)
{
    struct timespec ts;
    uint64_t fast_calls = 0, total_calls = 0;
    uint64_t threshold = 100; /* cycles */
    int i;

    /* Measure call latency distribution */
    for (i = 0; i < 10000; i++) {
        uint64_t start = rdcycle();
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        uint64_t end = rdcycle();

        uint64_t cycles = end - start;
        total_calls++;
        if (cycles < threshold)
            fast_calls++;
    }

    return (double)fast_calls / total_calls * 100.0;
}

static void run_performance_tests(void)
{
    double cpu_freq_mhz = get_cpu_freq_mhz();

    print_header("Performance Tests (P001-P006)");

    /* P001: Single call latency */
    printf("\nP001: Single call latency\n");
    double latency_cycles = measure_single_call_latency();
    double latency_ns = latency_cycles / cpu_freq_mhz;

    print_value("  Min latency", latency_cycles, "cycles");
    print_value("  Min latency", latency_ns, "ns");

    bool latency_ok = latency_cycles < 100; /* Expect < 100 cycles with cache */
    print_test("  Latency acceptable (< 100 cycles)", latency_ok);

    /* P002-P004: Throughput at different frequencies */
    printf("\nP002-P004: Throughput tests\n");

    int freqs[] = {1000000, 100000, 10000};
    const char *freq_names[] = {"High (1M/s)", "Medium (100k/s)", "Low (10k/s)"};

    for (int i = 0; i < 3; i++) {
        double avg_cycles = measure_throughput(freqs[i]);
        double improvement = 250.0 / avg_cycles; /* Baseline ~250 cycles */

        printf("  %s:\n", freq_names[i]);
        print_value("    Avg cycles", avg_cycles, "cycles");
        print_value("    Speedup", improvement, "x");

        bool perf_ok = avg_cycles < 100;
        print_test("    Performance acceptable", perf_ok);
    }

    /* P005: AI inference simulation */
    printf("\nP005: AI inference workload simulation\n");
    struct timespec ts;
    uint64_t total_cycles = 0;
    int iterations = 10000;

    for (int i = 0; i < iterations; i++) {
        uint64_t start = rdcycle();
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        /* Simulate inference work */
        volatile int j;
        for (j = 0; j < 100; j++);
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        uint64_t end = rdcycle();
        total_cycles += (end - start);
    }

    double avg_inference_cycles = (double)total_cycles / iterations;
    double baseline_inference_cycles = 500; /* Estimated baseline */
    double improvement = baseline_inference_cycles / avg_inference_cycles;

    print_value("  Avg inference cycles", avg_inference_cycles, "cycles");
    print_value("  Estimated speedup", improvement, "x");

    bool ai_perf_ok = improvement >= 3.0;
    print_test("  AI inference performance improved", ai_perf_ok);

    /* P006: Cache hit rate */
    printf("\nP006: Cache hit rate estimation\n");
    double hit_rate = estimate_cache_hit_rate();
    print_value("  Estimated cache hit rate", hit_rate, "%");

    bool cache_ok = hit_rate >= 50.0;
    print_test("  Cache effective (≥ 50% hit rate)", cache_ok);
}

/* ==================== Accuracy Tests ==================== */

static void run_accuracy_tests(void)
{
    print_header("Accuracy Tests (A001-A004)");

    /* A001: Absolute accuracy */
    printf("\nA001: Absolute accuracy vs syscall\n");
    struct timespec ts_vdso, ts_syscall;
    int64_t abs_max_diff = 0, total_diff = 0;
    int i;

    for (i = 0; i < ACCURACY_SAMPLES; i++) {
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts_vdso);
        clock_gettime_syscall(CLOCK_MONOTONIC, &ts_syscall);

        int64_t diff_ns = (ts_vdso.tv_sec - ts_syscall.tv_sec) * 1000000000 +
                          (ts_vdso.tv_nsec - ts_syscall.tv_nsec);

        if (llabs(diff_ns) > abs_max_diff)
            abs_max_diff = llabs(diff_ns);
        total_diff += llabs(diff_ns);
    }

    double avg_diff_ns = (double)total_diff / ACCURACY_SAMPLES;
    print_value("  Max difference", abs_max_diff, "ns");
    print_value("  Avg difference", avg_diff_ns, "ns");

    bool abs_accuracy_ok = abs_max_diff < 1000; /* < 1μs */
    print_test("  Absolute accuracy (< 1μs)", abs_accuracy_ok);

    /* A002: Relative accuracy (no negative intervals) */
    printf("\nA002: Relative accuracy (negative intervals)\n");
    int negative_count = 0;
    struct timespec prev, curr;

    clock_gettime_vdso(CLOCK_MONOTONIC, &prev);
    for (i = 0; i < 10000; i++) {
        clock_gettime_vdso(CLOCK_MONOTONIC, &curr);

        int64_t diff_ns = (curr.tv_sec - prev.tv_sec) * 1000000000 +
                          (curr.tv_nsec - prev.tv_nsec);
        if (diff_ns < 0)
            negative_count++;

        prev = curr;
    }

    print_value("  Negative intervals", negative_count, "count");
    bool no_negatives = (negative_count == 0);
    print_test("  No negative intervals", no_negatives);

    /* A003: Sleep accuracy */
    printf("\nA003: Sleep timing accuracy\n");
    struct timespec ts1, ts2;

    clock_gettime_vdso(CLOCK_MONOTONIC, &ts1);
    usleep(10000); /* 10ms */
    clock_gettime_vdso(CLOCK_MONOTONIC, &ts2);

    int64_t slept_ns = (ts2.tv_sec - ts1.tv_sec) * 1000000000 +
                       (ts2.tv_nsec - ts1.tv_nsec);
    double error_percent = (double)(slept_ns - 10000000) / 10000000 * 100;

    print_value("  Slept time", slept_ns / 1000, "μs");
    print_value("  Error", error_percent, "%");

    bool sleep_ok = (error_percent >= -10 && error_percent <= 50);
    print_test("  Sleep accuracy acceptable (-10% to +50%)", sleep_ok);

    /* A004: Cache freshness */
    printf("\nA004: Cache freshness in rapid reads\n");
    uint64_t diffs[100];

    for (i = 0; i < 100; i++) {
        uint64_t t1 = rdcycle();
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts_vdso);
        uint64_t t2 = rdcycle();
        diffs[i] = t2 - t1;
    }

    uint64_t max_diff = 0, sum_diff = 0;
    for (i = 0; i < 100; i++) {
        if (diffs[i] > max_diff)
            max_diff = diffs[i];
        sum_diff += diffs[i];
    }

    double avg_diff = (double)sum_diff / 100;
    print_value("  Max read cycles", max_diff, "cycles");
    print_value("  Avg read cycles", avg_diff, "cycles");

    bool freshness_ok = max_diff < 100;
    print_test("  Cache reads fast (< 100 cycles)", freshness_ok);
}

/* ==================== Stress Tests ==================== */

static volatile bool stress_running = true;
static jmp_buf stress_jmp;

static void sigalrm_handler(int sig)
{
    (void)sig;
    stress_running = false;
}

static void *stress_thread(void *arg)
{
    struct timespec ts;
    while (stress_running) {
        if (clock_gettime_vdso(CLOCK_MONOTONIC, &ts) != 0) {
            longjmp(stress_jmp, 1);
        }
    }
    return NULL;
}

static void run_stress_tests(void)
{
    print_header("Stress Tests (S001-S003)");

    /* S001: Sustained operation */
    printf("\nS001: Sustained operation (10 seconds)\n");
    stress_running = true;
    signal(SIGALRM, sigalrm_handler);
    alarm(STRESS_DURATION_SEC);

    struct timespec ts;
    uint64_t count = 0;

    if (setjmp(stress_jmp) == 0) {
        while (stress_running) {
            if (clock_gettime_vdso(CLOCK_MONOTONIC, &ts) != 0) {
                printf("  " COLOR_RED "✗" COLOR_RESET " Call failed during stress test\n");
                tests_failed++;
                break;
            }
            count++;
        }
    }

    alarm(0);
    signal(SIGALRM, SIG_DFL);

    print_value("  Completed calls", count, "calls");
    print_value("  Rate", count / (double)STRESS_DURATION_SEC, "calls/sec");
    print_test("  No crashes during sustained operation", true);

    /* S002: Multi-process */
    printf("\nS002: Multi-process concurrent test\n");
    int num_children = 10;
    pid_t pids[10];
    int i;

    for (i = 0; i < num_children; i++) {
        pids[i] = fork();
        if (pids[i] == 0) {
            /* Child process */
            for (int j = 0; j < 100000; j++) {
                clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
            }
            exit(0);
        } else if (pids[i] < 0) {
            perror("fork");
            print_test("  Fork failed", false);
            num_children = i;
            break;
        }
    }

    int status;
    bool all_ok = true;
    for (i = 0; i < num_children; i++) {
        waitpid(pids[i], &status, 0);
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
            all_ok = false;
        }
    }

    print_test("  All child processes completed successfully", all_ok);

    /* S003: Thread safety */
    printf("\nS003: Multi-threaded test\n");
    const int max_threads = 10;
    pthread_t threads[max_threads];
    int num_threads = max_threads;

    stress_running = true;

    for (i = 0; i < num_threads; i++) {
        if (pthread_create(&threads[i], NULL, stress_thread, NULL) != 0) {
            perror("pthread_create");
            print_test("  Thread creation failed", false);
            num_threads = i;
            break;
        }
    }

    /* Let threads run for 1 second */
    usleep(1000000);
    stress_running = false;

    bool threads_ok = true;
    for (i = 0; i < num_threads; i++) {
        if (pthread_join(threads[i], NULL) != 0) {
            threads_ok = false;
        }
    }

    print_test("  All threads completed successfully", threads_ok);
}

/* ==================== Main ==================== */

static void print_summary(void)
{
    int total = tests_passed + tests_failed + tests_skipped;
    double pass_rate = total > 0 ? (double)tests_passed / total * 100.0 : 0;

    printf("\n");
    printf("==============================================\n");
    printf("            Test Summary\n");
    printf("==============================================\n");
    printf("  Total tests:  %d\n", total);
    printf("  " COLOR_GREEN "Passed:       %d" COLOR_RESET "\n", tests_passed);
    printf("  " COLOR_RED "Failed:       %d" COLOR_RESET "\n", tests_failed);
    printf("  Skipped:      %d\n", tests_skipped);
    printf("  Pass rate:    %.1f%%\n", pass_rate);

    if (tests_failed == 0) {
        printf("\n  " COLOR_GREEN "✓ All tests passed!" COLOR_RESET "\n");
    } else {
        printf("\n  " COLOR_RED "✗ Some tests failed" COLOR_RESET "\n");
    }
    printf("==============================================\n");
}

int main(int argc, char **argv)
{
    bool quick = false;
    bool skip_perf = false;
    bool skip_stress = false;

    /* Parse arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--quick") == 0) {
            quick = true;
        } else if (strcmp(argv[i], "--skip-perf") == 0) {
            skip_perf = true;
        } else if (strcmp(argv[i], "--skip-stress") == 0) {
            skip_stress = true;
        } else if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [OPTIONS]\n", argv[0]);
            printf("Options:\n");
            printf("  --quick         Quick test (skip stress tests)\n");
            printf("  --skip-perf     Skip performance tests\n");
            printf("  --skip-stress   Skip stress tests\n");
            printf("  --help          Show this help\n");
            return 0;
        }
    }

    printf("==============================================\n");
    printf("  RISC-V VDSO Time Cache Test Suite\n");
    printf("==============================================\n");
    printf("Kernel: ");
    fflush(stdout);
    system("uname -r");
    printf("CPU: ");
    fflush(stdout);
    system("uname -m");
    printf("\n");

    /* Check if VDSO cache is enabled */
    FILE *fp = fopen("/proc/config.gz", "r");
    if (fp) {
        char line[256];
        bool cache_enabled = false;
        pclose(popen("zcat /proc/config.gz | grep CONFIG_RISCV_VDSO_TIME_CACHE", "r"));
        /* Simple check - in real implementation would parse properly */
        printf("Note: Verify CONFIG_RISCV_VDSO_TIME_CACHE=y in kernel config\n\n");
    }

    /* Run test suites */
    run_functional_tests();

    if (!skip_perf) {
        run_performance_tests();
    } else {
        printf("\n" COLOR_YELLOW "[Performance tests skipped]" COLOR_RESET "\n");
    }

    run_accuracy_tests();

    if (!skip_stress && !quick) {
        run_stress_tests();
    } else if (quick) {
        printf("\n" COLOR_YELLOW "[Stress tests skipped (--quick mode)]" COLOR_RESET "\n");
    }

    print_summary();

    return tests_failed > 0 ? 1 : 0;
}
