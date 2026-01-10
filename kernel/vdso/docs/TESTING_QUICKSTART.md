# RISC-V VDSO 时间缓存测试快速指南

## 快速开始

### 1. 准备环境

确保内核已启用 VDSO 时间缓存：
```bash
zcat /proc/config.gz | grep CONFIG_RISCV_VDSO_TIME_CACHE
# 应该显示: CONFIG_RISCV_VDSO_TIME_CACHE=y
```

### 2. 编译测试程序

```bash
# 方法一：使用 Makefile
make -f Makefile.test build

# 方法二：手动编译
gcc -O2 -o vdso_cache_test vdso_cache_test.c -lrt -lpthread
```

### 3. 运行测试

```bash
# 快速测试 (约1分钟)
sudo ./vdso_cache_test --quick

# 完整测试 (约5-10分钟)
sudo ./vdso_cache_test

# 仅性能测试
sudo ./vdso_cache_test --skip-stress

# 使用自动化脚本
chmod +x run_tests.sh
sudo ./run_tests.sh --quick
```

### 4. 查看结果

测试程序会输出：
- ✓ 绿色标记表示通过
- ✗ 红色标记表示失败
- 详细性能数据 (周期数、纳秒数、速度提升倍数)

## 预期结果

### 启用缓存 (CONFIG_RISCV_VDSO_TIME_CACHE=y)

```
Performance Tests (P001-P006)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P001: Single call latency
  • Min latency: 20.50 cycles
  • Min latency: 17.08 ns
  ✓ Latency acceptable (< 100 cycles)

P002-P004: Throughput tests
  High (1M/s):
    • Avg cycles: 25.30 cycles
    • Speedup: 9.88x
    ✓ Performance acceptable
  ...
```

### 禁用缓存 (对比基准)

```
Performance Tests (P001-P006)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P001: Single call latency
  • Min latency: 250.00 cycles
  • Min latency: 208.33 ns
  ✗ Latency acceptable (< 100 cycles)
```

## 对比测试方法

### 方法一：编译时配置

```bash
# 1. 编译无缓存版本
cd /path/to/linux
make menuconfig
# 取消选择: CONFIG_RISCV_VDSO_TIME_CACHE
make -j$(nproc)
sudo reboot

# 2. 运行基准测试
sudo ./vdso_cache_test > baseline.txt

# 3. 编译有缓存版本
make menuconfig
# 启用: CONFIG_RISCV_VDSO_TIME_CACHE
make -j$(nproc)
sudo reboot

# 4. 运行优化测试
sudo ./vdso_cache_test > cached.txt

# 5. 对比结果
diff baseline.txt cached.txt
```

### 方法二：运行时禁用

某些测试程序可以通过环境变量或参数禁用缓存（需修改代码支持）。

## 常见问题

### Q: 测试显示性能没有提升

A: 检查以下几点：
1. 确认 CONFIG_RISCV_VDSO_TIME_CACHE=y
2. 检查是否在高频调用场景下测试
3. 确认内核已正确重新编译并安装
4. 尝试运行 `sudo ./vdso_cache_test --performance` 查看详细数据

### Q: 精度测试失败

A: 小的精度损失是预期的：
- 缓存有效期内的连续调用可能返回相同时间值
- 这是正常的，换取的是性能提升
- 精度误差应 < 1μs

### Q: 系统崩溃或段错误

A:
1. 确保使用 root 权限运行
2. 检查内核日志: `dmesg | grep -i vdso`
3. 确认测试程序与内核版本匹配

## 性能基线参考

| 指标 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 单次调用 | ~250 周期 | ~20-50 周期 | 5-12x |
| 吞吐量 | 328k/s | 2.6M+/s | 8x |
| AI 推理 | 基准 | 提升 70-95% | 3-10x |

## 高级用法

### perf 集成

```bash
# 查看 CSR_TIME 指令统计
perf stat -e cycles,instructions,riscv_ht_instructions_retired \
    sudo ./vdso_cache_test

# 查看函数调用图
perf record -g sudo ./vdso_cache_test
perf report
```

### 自定义测试参数

修改源码中的宏定义：
```c
#define TEST_ITERATIONS       1000000  // 增加迭代次数
#define WARMUP_ITERATIONS     10000    // 调整预热次数
#define STRESS_DURATION_SEC   30       // 延长压力测试时间
```

## 联系与支持

- 详细文档: `VDSO_Time_Cache_Test_Plan.md`
- 性能分析: `RISC-V_VDSO_Performance_Analysis.md`
- 内核补丁: `riscv-vdso-cache-patch/`

## 下一步

1. 运行完整测试套件
2. 记录基线数据
3. 在实际工作负载中验证
4. 报告任何发现的问题
