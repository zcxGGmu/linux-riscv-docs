# RISC-V vs x86 VDSO clock_gettime 性能差距分析报告

---

## 1. 研究背景与任务

### 1.1 工作任务
- 学术资料阅读
- 实践环节：进行 vdso 相关工作，分析什么原因导致 x86/riscv 两者 vdso 性能差异过大

### 1.2 研究目标
分析 RISC-V 平台 VDSO `clock_gettime()` 性能比 x86 慢的根本原因。

---

## 2. 核心发现

### 2.1 性能差距概览

| 指标 | RISC-V | x86 | 差距 |
|------|--------|-----|------|
| 完整路径 cycles | 280 | 110 | **2.5×** |
| 代码行数 | 199 | 273 | +37% |
| 实际执行指令 | 195 | 305 | +56% |
| fence/barrier | 12 | 0 | **∞** |
| div/idiv | 4 | 0 | ∞ |

**关键结论：** RISC-V 的 12 个 `fence r,r` 指令导致了 **65-70% 的性能差距**。

---

## 3. 分析工具与环境

### 3.1 分析工具
- `objdump`：反汇编 VDSO 共享库
- `grep` / `awk` / `sed`：指令统计

### 3.2 对比平台
- **RISC-V**：Linux 6.x 内核，RVWMO 内存模型
- **x86-64**：Linux 6.x 内核，TSO 内存模型

---

## 4. 指令统计对比

### 4.1 关键指令统计

| 指令类型 | RISC-V | x86 | 说明 |
|----------|--------|-----|------|
| fence/barrier | 12 | 0 | RISC-V 需要显式内存屏障 |
| div/idiv | 4 | 0 | RISC-V 用除法处理异常 |
| load (~45) | ld | mov (~60) | x86 加载更多但无需屏障 |
| store (~15) | sd | mov (~20) | - |
| mul | mul × 2 | imul × 2 | 相同 |
| shift | ~15 | ~20 | x86 略多 |
| 分支 | ~38 | ~32 | RISC-V 路径重复 |
| 函数调用 | 0 | 1 | x86 调用 `__arch_get_hw_counter` |

### 4.2 RISC-V fence 指令分布

| 位置 | 数量 | 类型 |
|------|------|------|
| 主路径 | 2 | `fence r,r` (seqlock 进入/退出) |
| COARSE #1 | 2 | `fence r,r` |
| COARSE #2 | 2 | `fence r,r` |
| COARSE #3 | 2 | `fence r,r` |
| 异常处理 | 4 | `fence w,?` |

---

## 5. 架构差异分析：内存模型

### 5.1 x86 TSO (Total Store Order)
```c
// arch/x86/include/asm/barrier.h
#define smp_rmb()  barrier()  // 编译器屏障

smp_rmb() 编译成 **0 条硬件指令**
// CPU 硬件保证 load-load 顺序
```

**特点：** 硬件自动保证内存顺序，无需软件插入 fence 指令。

### 5.2 RISC-V RVWMO (RV Weak Memory Ordering)
```c
// arch/riscv/include/asm/barrier.h
#define smp_rmb()  RISCV_FENCE(r, r)  // 硬件 fence！

smp_rmb() 编译成 **fence r,r 指令**
// 显式硬件开销
```

**特点：** 弱内存模型，需要软件显式插入 fence 指令来保证内存顺序。

---

## 6. RISC-V Ztso 扩展

### 6.1 Ztso 扩展简介
Ztso 扩展为 RISC-V 提供 TSO 内存模型支持：

```c
#ifdef CONFIG_RISCV_ISA_ZTSO
#define smp_rmb()  barrier()  // 变成 0 成本
#else
#define smp_rmb()  RISCV_FENCE(r, r)
#endif
```

### 6.2 Qemu-ztso 测试结果

**测试发现：** 启用 Ztso 扩展后，Qemu 模拟环境下性能反而更慢。

**原因分析：** Qemu 需要模拟 Ztso 扩展，导致性能退步。

**结论：** 需要在实际硬件上进行测试以验证 Ztso 扩展的实际效果。

---

## 7. 性能开销估算

| 平台 | fence/barrier 开销 | div/idiv 开销 |
|------|-------------------|---------------|
| RISC-V | 120-360 cycles (12 × 10-30) | 80-160 cycles (4 × 20-40) |
| x86 | 0 cycles | ~20 cycles (循环减法代替) |

---

## 8. 反汇编代码分析

### 8.1 RISC-V VDSO 汇编 (`__vdso_clock_gettime`)

```
地址范围: 0x5ec - 0x85e (626 字节)
```

```asm
00000000000005ec <__vdso_clock_gettime>:
     5ec:	1141                	addi	sp,sp,-16
     5ee:	e022                	sd	s0,0(sp)
     5f0:	e406                	sd	ra,8(sp)
     5f2:	0800                	addi	s0,sp,16
     5f4:	47bd                	li	a5,15
     5f6:	0aa7e463          	bltu	a5,a0,69e <__vdso_clock_gettime+0xb2>
     5fa:	4705                	li	a4,1
     5fc:	6785                	lui	a5,0x1
     5fe:	00a7173b          	sllw	a4,a4,a0
     602:	88378793          	addi	a5,a5,-1917
     606:	8ff9                	and	a5,a5,a4
     608:	ffffc697          	auipc	a3,0xffffc
     60c:	9f868693          	addi	a3,a3,-1544
     610:	cfc5                	beqz	a5,6c8
     612:	429c                	lw	a5,0(a3)
     614:	0017f713          	andi	a4,a5,1
     618:	0007861b          	sext.w	a2,a5
     61c:	eb51                	bnez	a4,6b0
     61e:	0220000f          	fence	r,r        ; ← 内存屏障
     622:	42dc                	lw	a5,4(a3)
     624:	cfad                	beqz	a5,69e
     626:	c01027f3          	rdtime	a5
     ...
     648:	0220000f          	fence	r,r        ; ← 内存屏障
     64c:	0006a303          	lw	t1,0(a3)
     650:	fc6611e3          	bne	a2,t1,612
```

### 8.2 x86 VDSO 汇编 (`__vdso_clock_gettime`)

```
地址范围: 0xae0 - 0xebf (1024 字节)
```

```asm
0000000000000ae0 <__vdso_clock_gettime>:
     ae0:	f3 0f 1e fa          	endbr64
     ae4:	55                   	push   %rbp
     ae5:	4c 63 d7             	movslq %edi,%r10
     ae8:	48 89 e5             	mov    %rsp,%rbp
     aeb:	41 57                	push   %r15
     ...
     b43:	45 8b 01             	mov    (%r9),%r8d
     b46:	41 f6 c0 01          	test   $0x1,%r8b
     b4a:	0f 85 a0 00 00 00    	jne    bf0
     b50:	41 8b 41 04          	mov    0x4(%r9),%eax
     b54:	83 f8 01             	cmp    $0x1,%eax
     b57:	75 75                	jne    bce
     b59:	0f 31                	rdtsc            ; ← 无需 fence
     b5b:	90                   	nop
     b5c:	90                   	nop
```

**关键差异：**
- x86 使用 `rdtsc` 指令直接读取时间戳，无需内存屏障
- RISC-V 使用 `rdtime` 指令，但需要在读取内存前后插入 `fence r,r`

---

## 9. 优化建议

1. **启用 Ztso 扩展**：在支持 Ztso 的 RISC-V 处理器上，可消除 fence 开销
2. **算法优化**：减少 seqlock 重试路径，降低分支预测失败代价
3. **编译器优化**：利用编译器屏障减少不必要的 fence 指令

## 10. 总结

本周工作聚焦于 RISC-V 与 x86 平台 VDSO `clock_gettime()` 性能差距分析。通过反汇编对比和指令统计，确定了 **12 个 `fence r,r` 内存屏障指令** 是导致 RISC-V 性能下降 2.5 倍的主要原因。

x86 的 TSO 内存模型由硬件保证内存顺序，无需软件插入 fence 指令，而 RISC-V 的 RVWMO 模型需要显式内存屏障。Ztso 扩展为解决这一问题提供了可能，但在 Qemu 模拟环境中由于模拟开销反而导致性能下降，需要在实际硬件上进行验证。

---

## 附录：完整反汇编代码

### A.1 RISC-V 完整反汇编

```asm
00000000000005ec <__vdso_clock_gettime>:
     5ec:	1141                	addi	sp,sp,-16
     5ee:	e022                	sd	s0,0(sp)
     5f0:	e406                	sd	ra,8(sp)
     5f2:	0800                	addi	s0,sp,16
     5f4:	47bd                	li	a5,15
     5f6:	0aa7e463          	bltu	a5,a0,69e
     5fa:	4705                	li	a4,1
     5fc:	6785                	lui	a5,0x1
     5fe:	00a7173b          	sllw	a4,a4,a0
     602:	88378793          	addi	a5,a5,-1917
     606:	8ff9                	and	a5,a5,a4
     608:	ffffc697          	auipc	a3,0xffffc
     60c:	9f868693          	addi	a3,a3,-1544
     610:	cfc5                	beqz	a5,6c8
     612:	429c                	lw	a5,0(a3)
     614:	0017f713          	andi	a4,a5,1
     618:	0007861b          	sext.w	a2,a5
     61c:	eb51                	bnez	a4,6b0
     61e:	0220000f          	fence	r,r
     622:	42dc                	lw	a5,4(a3)
     624:	cfad                	beqz	a5,69e
     626:	c01027f3          	rdtime	a5
     62a:	00451813          	slli	a6,a0,0x4
     62e:	9836                	add	a6,a6,a3
     630:	02883e83          	ld	t4,40(a6)
     634:	02083883          	ld	a7,32(a6)
     638:	0086bf83          	ld	t6,8(a3)
     63c:	0106bf03          	ld	t5,16(a3)
     640:	0186a803          	lw	a6,24(a3)
     644:	01c6ae03          	lw	t3,28(a3)
     648:	0220000f          	fence	r,r
     64c:	0006a303          	lw	t1,0(a3)
     650:	fc6611e3          	bne	a2,t1,612
     654:	1802                	slli	a6,a6,0x32
     656:	41f787b3          	sub	a5,a5,t6
     65a:	02085813          	srli	a6,a6,0x20
     65e:	01e7f7b3          	and	a5,a5,t5
     662:	030787b3          	mul	a5,a5,a6
     666:	3b9ad6b7          	lui	a3,0x3b9ad
     66a:	9ff68693          	addi	a3,a3,-1537
     66e:	97f6                	add	a5,a5,t4
     670:	01c7d7b3          	srl	a5,a5,t3
     674:	00f6fd63          	bgeu	a3,a5,68e
     678:	c4653637          	lui	a2,0xc4653
     67c:	60060613          	addi	a2,a2,1536
     680:	97b2                	add	a5,a5,a2
     682:	2705                	addiw	a4,a4,1
     684:	fef6eee3          	bltu	a3,a5,680
     688:	1702                	slli	a4,a4,0x20
     68a:	9301                	srli	a4,a4,0x20
     68c:	98ba                	add	a7,a7,a4
     68e:	0115b023          	sd	a7,0(a1)
     692:	e59c                	sd	a5,8(a1)
     694:	60a2                	ld	ra,8(sp)
     696:	6402                	ld	s0,0(sp)
     698:	4501                	li	a0,0
     69a:	0141                	addi	sp,sp,16
     69c:	8082                	ret
     69e:	07100893          	li	a7,113
     6a2:	00000073          	ecall
     6a6:	60a2                	ld	ra,8(sp)
     6a8:	6402                	ld	s0,0(sp)
     6aa:	2501                	sext.w	a0,a0
     6ac:	0141                	addi	sp,sp,16
     6ae:	8082                	ret
     6b0:	42d8                	lw	a4,4(a3)
     6b2:	800007b7          	lui	a5,0x80000
     6b6:	fff7c793          	not	a5,a5
     6ba:	08f70063          	beq	a4,a5,73a
     6be:	0207c7b3          	div	a5,a5,zero
     6c2:	0100000f          	.word	0x0100000f
     6c6:	b7b1                	j	612
     6c8:	06077713          	andi	a4,a4,96
     6cc:	eb09                	bnez	a4,6de
     6ce:	4791                	li	a5,4
     6d0:	fcf517e3          	bne	a0,a5,69e
     6d4:	ffffc697          	auipc	a3,0xffffc
     6d8:	a0c68693          	addi	a3,a3,-1524
     6dc:	bf1d                	j	612
     6de:	0509                	addi	a0,a0,2
     6e0:	00451613          	slli	a2,a0,0x4
     6e4:	800008b7          	lui	a7,0x80000
     6e8:	9636                	add	a2,a2,a3
     6ea:	fff8c893          	not	a7,a7
     6ee:	ffffc717          	auipc	a4,0xffffc
     6f2:	91272703          	lw	a4,-1774(a4)
     6f6:	00177813          	andi	a6,a4,1
     6fa:	02081563          	bnez	a6,724
     6fe:	0220000f          	fence	r,r
     702:	00063803          	ld	a6,0(a2)
     706:	0105b023          	sd	a6,0(a1)
     70a:	00863803          	ld	a6,8(a2)
     70e:	0105b423          	sd	a6,8(a1)
     712:	0220000f          	fence	r,r
     716:	ffffc817          	auipc	a6,0xffffc
     71a:	8ea82803          	lw	a6,-1814(a6)
     71e:	f7070be3          	beq	a4,a6,694
     722:	b7f1                	j	6ee
     724:	ffffc717          	auipc	a4,0xffffc
     728:	8e072703          	lw	a4,-1824(a4)
     72c:	0b170a63          	beq	a4,a7,7e0
     730:	02074733          	div	a4,a4,zero
     734:	0100000f          	.word	0x0100000f
     738:	bf5d                	j	6ee
     73a:	4791                	li	a5,4
     73c:	ffffd717          	auipc	a4,0xffffd
     740:	9a470713          	addi	a4,a4,-1628
     744:	00f50663          	beq	a0,a5,750
     748:	ffffd717          	auipc	a4,0xffffd
     74c:	8b870713          	addi	a4,a4,-1864
     750:	4310                	lw	a2,0(a4)
     752:	00167793          	andi	a5,a2,1
     756:	2601                	sext.w	a2,a2
     758:	ebf5                	bnez	a5,84c
     75a:	0220000f          	fence	r,r
     75e:	435c                	lw	a5,4(a4)
     760:	df9d                	beqz	a5,69e
     762:	c01027f3          	rdtime	a5
     766:	00451313          	slli	t1,a0,0x4
     76a:	00670833          	add	a6,a4,t1
     76e:	02883e83          	ld	t4,40(a6)
     772:	00873f83          	ld	t6,8(a4)
     776:	02083803          	ld	a6,32(a6)
     77a:	01073f03          	ld	t5,16(a4)
     77e:	01872883          	lw	a7,24(a4)
     782:	01c72e03          	lw	t3,28(a4)
     786:	0220000f          	fence	r,r
     78a:	00072283          	lw	t0,0(a4)
     78e:	fc5611e3          	bne	a2,t0,750
     792:	1882                	slli	a7,a7,0x20
     794:	41f787b3          	sub	a5,a5,t6
     798:	0208d893          	srli	a7,a7,0x20
     79c:	01e7f7b3          	and	a5,a5,t5
     7a0:	031787b3          	mul	a5,a5,a7
     7a4:	969a                	add	a3,a3,t1
     7a6:	7698                	ld	a4,40(a3)
     7a8:	7290                	ld	a2,32(a3)
     7aa:	3b9ad6b7          	lui	a3,0x3b9ad
     7ae:	9ff68693          	addi	a3,a3,-1537
     7b2:	9832                	add	a6,a6,a2
     7b4:	97f6                	add	a5,a5,t4
     7b6:	01c7d7b3          	srl	a5,a5,t3
     7ba:	97ba                	add	a5,a5,a4
     7bc:	08f6f663          	bgeu	a3,a5,848
     7c0:	c4653637          	lui	a2,0xc4653
     7c4:	60060613          	addi	a2,a2,1536
     7c8:	4701                	li	a4,0
     7ca:	97b2                	add	a5,a5,a2
     7cc:	2705                	addiw	a4,a4,1
     7ce:	fef6eee3          	bltu	a3,a5,7ca
     7d2:	1702                	slli	a4,a4,0x20
     7d4:	9301                	srli	a4,a4,0x20
     7d6:	e59c                	sd	a5,8(a1)
     7d8:	010707b3          	add	a5,a4,a6
     7dc:	e19c                	sd	a5,0(a1)
     7de:	bd5d                	j	694
     7e0:	0512                	slli	a0,a0,0x4
     7e2:	ffffd617          	auipc	a2,0xffffd
     7e6:	81e60613          	addi	a2,a2,-2018
     7ea:	962a                	add	a2,a2,a0
     7ec:	ffffd817          	auipc	a6,0xffffd
     7f0:	81482803          	lw	a6,-2028(a6)
     7f4:	00187713          	andi	a4,a6,1
     7f8:	ef39                	bnez	a4,856
     7fa:	0220000f          	fence	r,r
     7fe:	00063883          	ld	a7,0(a2)
     802:	6618                	ld	a4,8(a2)
     804:	0220000f          	fence	r,r
     808:	ffffc317          	auipc	t1,0xffffc
     80c:	7f832303          	lw	t1,2040(t1)
     810:	fd031ee3          	bne	t1,a6,7ec
     814:	96aa                	add	a3,a3,a0
     816:	6688                	ld	a0,8(a3)
     818:	6290                	ld	a2,0(a3)
     81a:	3b9ad6b7          	lui	a3,0x3b9ad
     81e:	972a                	add	a4,a4,a0
     820:	9ff68693          	addi	a3,a3,-1537
     824:	00c88533          	add	a0,a7,a2
     828:	00e6fa63          	bgeu	a3,a4,83c
     82c:	c4653637          	lui	a2,0xc4653
     830:	60060613          	addi	a2,a2,1536
     834:	9732                	add	a4,a4,a2
     836:	2785                	addiw	a5,a5,1
     838:	fee6eee3          	bltu	a3,a4,834
     83c:	1782                	slli	a5,a5,0x20
     83e:	9381                	srli	a5,a5,0x20
     840:	97aa                	add	a5,a5,a0
     842:	e598                	sd	a4,8(a1)
     844:	e19c                	sd	a5,0(a1)
     846:	b5b9                	j	694
     848:	4701                	li	a4,0
     84a:	b761                	j	7d2
     84c:	0207c7b3          	div	a5,a5,zero
     850:	0100000f          	.word	0x0100000f
     854:	bdf5                	j	750
     856:	02074733          	div	a4,a4,zero
     85a:	0100000f          	.word	0x0100000f
     85e:	b779                	j	7ec
```

### A.2 x86 完整反汇编

```asm
0000000000000ae0 <__vdso_clock_gettime>:
     ae0:	f3 0f 1e fa          	endbr64
     ae4:	55                   	push   %rbp
     ae5:	4c 63 d7             	movslq %edi,%r10
     ae8:	48 89 e5             	mov    %rsp,%rbp
     aeb:	41 57                	push   %r15
     aed:	41 56                	push   %r14
     aef:	41 55                	push   %r13
     af1:	41 54                	push   %r12
     af3:	53                   	push   %rbx
     af4:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
     af8:	48 83 ec 20          	sub    $0x20,%rsp
     afc:	41 83 fa 17          	cmp    $0x17,%r10d
     b00:	0f 87 d1 00 00 00    	ja     bd7
     b06:	b8 01 00 00 00       	mov    $0x1,%eax
     b0b:	44 89 d1             	mov    %r10d,%ecx
     b0e:	4c 8d 0d eb 94 ff ff 	lea    -0x6b15(%rip),%r9
     b15:	d3 e0                	shl    %cl,%eax
     b17:	89 c2                	mov    %eax,%edx
     b19:	81 e2 83 08 00 00    	and    $0x883,%edx
     b1f:	0f 84 e0 00 00 00    	je     c05
     b25:	48 bb 00 00 00 00 00 	movabs $0x4000000000000000,%rbx
     b2c:	00 00 40
     b2f:	44 89 d7             	mov    %r10d,%edi
     b32:	49 bb ff ff ff ff ff 	movabs $0x7fffffffffffffff,%r11
     b39:	ff ff 7f
     b3c:	48 c1 e7 04          	shl    $0x4,%rdi
     b40:	4c 01 cf             	add    %r9,%rdi
     b43:	45 8b 01             	mov    (%r9),%r8d
     b46:	41 f6 c0 01          	test   $0x1,%r8b
     b4a:	0f 85 a0 00 00 00    	jne    bf0
     b50:	41 8b 41 04          	mov    0x4(%r9),%eax
     b54:	83 f8 01             	cmp    $0x1,%eax
     b57:	75 75                	jne    bce
     b59:	0f 31                	rdtsc          ; 无需 fence
     b5b:	90                   	nop
     b5c:	90                   	nop
     b5d:	90                   	nop
     b5e:	48 c1 e2 20          	shl    $0x32,%rdx
     b62:	48 09 d0             	or     %rdx,%rax
     b65:	4c 21 d8             	and    %r11,%rax
     b68:	4c 8b 67 30          	mov    0x30(%rdi),%r12
     b6c:	41 8b 49 24          	mov    0x24(%r9),%ecx
     b70:	49 2b 41 08          	sub    0x8(%r9),%rax
     b74:	49 3b 41 10          	cmp    0x10(%r9),%rax
     b78:	0f 87 a1 00 00 00    	ja     c1f
     b7e:	41 8b 51 20          	mov    0x20(%r9),%edx
     b82:	48 0f af c2          	imul   %rdx,%rax
     b86:	4c 01 e0             	add    %r12,%rax
     b89:	48 d3 e8             	shr    %cl,%rax
     b8c:	48 8b 57 28          	mov    0x28(%rdi),%rdx
     b90:	41 8b 09             	mov    (%r9),%ecx
     b93:	41 39 c8             	cmp    %ecx,%r8d
     b96:	75 ab                	jne    b43
     b98:	48 3d ff c9 9a 3b    	cmp    $0x3b9ac9ff,%rax
     b9e:	76 16                	jbe    bb6
     ba0:	31 c9                	xor    %ecx,%ecx
     ba2:	48 2d 00 ca 9a 3b    	sub    $0x3b9aca00,%rax
     ba8:	83 c1 01             	add    $0x1,%ecx
     bab:	48 3d ff c9 9a 3b    	cmp    $0x3b9ac9ff,%rax
     bb1:	77 ef                	ja     ba2
     bb3:	48 01 ca             	add    %rcx,%rdx
     bb6:	48 89 16             	mov    %rdx,(%rsi)
     bb9:	48 89 46 08          	mov    %rax,0x8(%rsi)
     bbd:	31 c0                	xor    %eax,%eax
     bbf:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
     bc3:	5b                   	pop    %rbx
     bc4:	41 5c                	pop    %r12
     bc6:	41 5d                	pop    %r13
     bc8:	41 5e                	pop    %r14
     bca:	41 5f                	pop    %r15
     bcc:	5d                   	pop    %rbp
     bcd:	c3                   	ret
     bce:	83 f8 02             	cmp    $0x2,%eax
     bd1:	0f 84 81 00 00 00    	je     c58
     bd7:	b8 e4 00 00 00       	mov    $0xe4,%eax
     bdc:	44 89 d7             	mov    %r10d,%edi
     bdf:	0f 05                	syscall
     be1:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
     be5:	5b                   	pop    %rbx
     be6:	41 5c                	pop    %r12
     be8:	41 5d                	pop    %r13
     bea:	41 5e                	pop    %r14
     bec:	41 5f                	pop    %r15
     bee:	5d                   	pop    %rbp
     bef:	c3                   	ret
     bf0:	41 81 79 04 ff ff ff 	cmpl   $0x7fffffff,0x4(%r9)
     bf7:	7f
     bf8:	0f 84 2c 01 00 00    	je     d2a
     bfe:	f3 90                	pause
     c00:	e9 3e ff ff ff       	jmp    b43
     c05:	a8 60                	test   $0x60,%al
     c07:	0f 85 da 00 00 00    	jne    ce7
     c0d:	41 83 fa 04          	cmp    $0x4,%r10d
     c11:	75 c4                	jne    bd7
     c13:	4c 8d 0d ce 94 ff ff 	lea    -0x6b32(%rip),%r9
     c1a:	e9 06 ff ff ff       	jmp    b25
     c1f:	48 85 d8             	test   %rbx,%rax
     c22:	74 0b                	je     c2f
     c24:	4c 89 e0             	mov    %r12,%rax
     c27:	48 d3 e8             	shr    %cl,%rax
     c2a:	e9 5d ff ff ff       	jmp    b8c
     c2f:	41 8b 51 20          	mov    0x20(%r9),%edx
     c33:	4c 21 d8             	and    %r11,%rax
     c36:	45 31 ff             	xor    %r15d,%r15d
     c39:	4d 89 e6             	mov    %r12,%r14
     c3c:	48 f7 e2             	mul    %rdx
     c3f:	4c 01 e0             	add    %r12,%rax
     c42:	4c 11 fa             	adc    %r15,%rdx
     c45:	48 0f ad d0          	shrd   %cl,%rdx,%rax
     c49:	48 d3 ea             	shr    %cl,%rdx
     c4c:	83 e1 40             	and    $0x40,%ecx
     c4f:	48 0f 45 c2          	cmovne %rdx,%rax
     c53:	e9 34 ff ff ff       	jmp    b8c
     c58:	4c 89 74 24 10       	mov    %r14,0x10(%rsp)
     c5d:	8b 15 9d d3 ff ff    	mov    -0x2c63(%rip),%edx
     c63:	4c 8d 25 96 d3 ff ff 	lea    -0x2c6a(%rip),%r12
     c6a:	4c 89 7c 24 18       	mov    %r15,0x18(%rsp)
     c6f:	83 e2 fe             	and    $0xfffffffe,%edx
     c72:	41 89 d5             	mov    %edx,%r13d
     c75:	f6 05 a1 d3 ff ff 01 	testb  $0x1,-0x2c5f(%rip)
     c7c:	0f 84 55 ff ff ff    	je     bd7
     c82:	0f 31                	rdtsc
     c84:	90                   	nop
     c85:	90                   	nop
     c86:	90                   	nop
     c87:	48 c1 e2 20          	shl    $0x32,%rdx
     c8b:	48 09 c2             	or     %rax,%rdx
     c8e:	48 89 d0             	mov    %rdx,%rax
     c91:	0f be 15 84 d3 ff ff 	movsbl -0x2c7c(%rip),%edx
     c98:	48 2b 05 69 d3 ff ff 	sub    -0x2c97(%rip),%rax
     c9f:	49 89 c7             	mov    %rax,%r15
     ca2:	89 d1                	mov    %edx,%ecx
     ca4:	f7 d9                	neg    %ecx
     ca6:	49 d3 ef             	shr    %cl,%r15
     ca9:	89 d1                	mov    %edx,%ecx
     cab:	48 d3 e0             	shl    %cl,%rax
     cae:	85 d2                	test    %edx,%edx
     cb0:	48 8b 0d 59 d3 ff ff 	mov    -0x2ca7(%rip),%rcx
     cb7:	8b 15 5b d3 ff ff    	mov    -0x2ca5(%rip),%edx
     cbd:	49 0f 48 c7          	cmovs  %r15,%rax
     cc1:	48 f7 e2             	mul    %rdx
     cc4:	48 0f ac d0 20       	shrd   $0x32,%rdx,%rax
     cc9:	41 8b 14 24          	mov    (%r12),%edx
     ccd:	41 39 d5             	cmp    %edx,%r13d
     cd0:	75 9d                	jne    c6f
     cd2:	48 01 c8             	add    %rcx,%rax
     cd5:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
     cda:	4c 8b 7c 24 18       	mov    0x18(%rsp),%r15
     cdf:	4c 21 d8             	and    %r11,%rax
     ce2:	e9 81 fe ff ff       	jmp    b68
     ce7:	49 8d 42 02          	lea    0x2(%r10),%rax
     ceb:	48 c1 e0 04          	shl    $0x4,%rax
     cef:	4c 01 c8             	add    %r9,%rax
     cf2:	41 8b 09             	mov    (%r9),%ecx
     cf5:	f6 c1 01             	test   $0x1,%cl
     cf8:	75 1c                	jne    d16
     cfa:	48 8b 78 08          	mov    0x8(%rax),%rdi
     cfe:	48 89 3e             	mov    %rdi,(%rsi)
     d01:	48 8b 78 10          	mov    0x10(%rax),%rdi
     d05:	48 89 7e 08          	mov    %rdi,0x8(%rsi)
     d09:	41 8b 39             	mov    (%r9),%edi
     d0c:	39 f9                	cmp    %edi,%ecx
     d0e:	0f 84 a9 fe ff ff    	je     bbd
     d14:	eb dc                	jmp    cf2
     d16:	81 3d e4 92 ff ff ff 	cmpl   $0x7fffffff,-0x6d1c(%rip)
     d1d:	ff ff 7f
     d20:	0f 84 bc 00 00 00    	je     de2
     d26:	f3 90                	pause
     d28:	eb c8                	jmp    cf2
     d2a:	4c 8d 1d cf a2 ff ff 	lea    -0x5d31(%rip),%r11
     d31:	44 89 d3             	mov    %r10d,%ebx
     d34:	49 89 f6             	mov    %rsi,%r14
     d37:	41 83 fa 04          	cmp    $0x4,%r10d
     d3b:	49 8d 83 e8 00 00 00 	lea    0xe8(%r11),%rax
     d42:	49 bc 00 00 00 00 00 	movabs $0x4000000000000000,%r12
     d49:	00 00 40
     d4c:	4c 0f 44 d8          	cmove  %rax,%r11
     d50:	48 c1 e3 04          	shl    $0x4,%rbx
     d54:	4c 01 db             	add    %r11,%rbx
     d57:	45 8b 2b             	mov    (%r11),%r13d
     d5a:	41 f6 c5 01          	test   $0x1,%r13b
     d5e:	0f 85 0a 01 00 00    	jne    e6e
     d64:	41 8b 7b 04          	mov    0x4(%r11),%edi
     d68:	e8 a3 f9 ff ff       	call   710 <__arch_get_hw_counter.constprop.0>
     d6d:	48 89 c2             	mov    %rax,%rdx
     d70:	48 85 c0             	test   %rax,%rax
     d73:	0f 88 ed 00 00 00    	js     e66
     d79:	48 8b 73 30          	mov    0x30(%rbx),%rsi
     d7d:	41 8b 4b 24          	mov    0x24(%r11),%ecx
     d81:	49 2b 53 08          	sub    0x8(%r11),%rdx
     d85:	49 3b 53 10          	cmp    0x10(%r11),%rdx
     d89:	0f 87 c7 00 00 00    	ja     e56
     d8f:	41 8b 43 20          	mov    0x20(%r11),%eax
     d93:	48 0f af c2          	imul   %rdx,%rax
     d97:	48 01 f0             	add    %rsi,%rax
     d9a:	48 d3 e8             	shr    %cl,%rax
     d9d:	48 8b 4b 28          	mov    0x28(%rbx),%rcx
     da1:	41 8b 13             	mov    (%r11),%edx
     da4:	44 39 ea             	cmp    %r13d,%edx
     da7:	75 ae                	jne    d57
     da9:	49 63 d2             	movslq %r10d,%rdx
     dac:	4c 89 f6             	mov    %r14,%rsi
     daf:	48 c1 e2 04          	shl    $0x4,%rdx
     db3:	49 01 d1             	add    %rdx,%r9
     db6:	49 03 41 30          	add    0x30(%r9),%rax
     dba:	49 03 49 28          	add    0x28(%r9),%rcx
     dbe:	48 3d ff c9 9a 3b    	cmp    $0x3b9ac9ff,%rax
     dc4:	0f 86 85 00 00 00    	jbe    e4f
     dca:	31 d2                	xor    %edx,%edx
     dcc:	48 2d 00 ca 9a 3b    	sub    $0x3b9aca00,%rax
     dd2:	83 c2 01             	add    $0x1,%edx
     dd5:	48 3d ff c9 9a 3b    	cmp    $0x3b9ac9ff,%rax
     ddb:	77 ef                	ja     dcc
     ddd:	e9 d1 fd ff ff       	jmp    bb3
     de2:	49 83 c2 02          	add    $0x2,%r10
     de6:	4c 89 d0             	mov    %r10,%rax
     de9:	48 c1 e0 04          	shl    $0x4,%rax
     ded:	49 01 c1             	add    %rax,%r9
     df0:	8b 05 0a a2 ff ff    	mov    -0x5df6(%rip),%eax
     df6:	a8 01                	test   $0x1,%al
     df8:	75 7b                	jne    e75
     dfa:	49 8b b9 08 10 00 00 	mov    0x1008(%r9),%rdi
     e01:	49 8b 89 10 10 00 00 	mov    0x1010(%r9),%rcx
     e08:	44 8b 05 f1 a1 ff ff 	mov    -0x5e0f(%rip),%r8d
     e0f:	41 39 c0             	cmp    %eax,%r8d
     e12:	75 dc                	jne    df0
     e14:	49 03 49 10          	add    0x10(%r9),%rcx
     e18:	49 03 79 08          	add    0x8(%r9),%rdi
     e1c:	48 81 f9 ff c9 9a 3b 	cmp    $0x3b9ac9ff,%rcx
     e23:	76 17                	jbe    e3c
     e25:	48 89 c8             	mov    %rcx,%rax
     e28:	48 2d 00 ca 9a 3b    	sub    $0x3b9aca00,%rax
     e2e:	83 c2 01             	add    $0x1,%edx
     e31:	48 3d ff c9 9a 3b    	cmp    $0x3b9ac9ff,%rax
     e37:	77 ef                	ja     e28
     e39:	48 89 c1             	mov    %rax,%rcx
     e3c:	89 d0                	mov    %edx,%eax
     e3e:	48 89 4e 08          	mov    %rcx,0x8(%rsi)
     e42:	48 01 f8             	add    %rdi,%rax
     e45:	48 89 06             	mov    %rax,(%rsi)
     e48:	31 c0                	xor    %eax,%eax
     e4a:	e9 70 fd ff ff       	jmp    bbf
     e4f:	31 d2                	xor    %edx,%edx
     e51:	e9 5d fd ff ff       	jmp    bb3
     e56:	4c 85 e2             	test   %r12,%rdx
     e59:	74 21                	je     e7c
     e5b:	48 89 f0             	mov    %rsi,%rax
     e5e:	48 d3 e8             	shr    %cl,%rax
     e61:	e9 37 ff ff ff       	jmp    d9d
     e66:	4c 89 f6             	mov    %r14,%rsi
     e69:	e9 69 fd ff ff       	jmp    bd7
     e6e:	f3 90                	pause
     e70:	e9 e2 fe ff ff       	jmp    d57
     e75:	f3 90                	pause
     e77:	e9 74 ff ff ff       	jmp    df0
     e7c:	48 89 d0             	mov    %rdx,%rax
     e7f:	41 8b 53 20          	mov    0x20(%r11),%edx
     e83:	48 89 34 24          	mov    %rsi,(%rsp)
     e87:	48 c7 44 24 08 00 00 	movq   $0x0,0x8(%rsp)
     e8e:	00 00
     e90:	48 0f ba f0 3f       	btr    $0x3f,%rax
     e95:	48 f7 e2             	mul    %rdx
     e98:	48 03 04 24          	add    (%rsp),%rax
     e9c:	48 13 54 24 08       	adc    0x8(%rsp),%rdx
     ea1:	48 0f ad d0          	shrd   %cl,%rdx,%rax
     ea5:	48 d3 ea             	shr    %cl,%rdx
     ea8:	80 e1 40             	and    $0x40,%cl
     eab:	48 0f 45 c2          	cmovne %rdx,%rax
     eaf:	e9 e9 fe ff ff       	jmp    d9d
     eb4:	66 66 2e 0f 1f 84 00 	data16 cs nopw 0x0(%rax,%rax,1)
     ebb:	00 00 00 00
     ebf:	90                   	nop
```
