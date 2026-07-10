# -1 参考

* https://elixir.bootlin.com/linux/latest/source/arch/riscv/kernel/signal.c#L116
* https://www.cnblogs.com/gnuemacs/p/14311120.html
* https://blog.csdn.net/u012075739/article/details/120319425
* https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter1/5support-func-call.html







# 0 规划





# 1 你必须要清楚的一些内容

## 1.1 关于函数调用栈

### 1) RISC-V function call support

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter1/5support-func-call.html

#### function call base

从汇编指令的级别看待一段程序的执行，假如 CPU 依次执行的指令的物理地址序列为 {𝑎𝑛}，那么这个序列会符合怎样的模式呢？

其中最简单的无疑就是 CPU 一条条连续向下执行指令，也即满足递推公式 𝑎𝑛+1=𝑎𝑛+𝐿，这里我们假设该平台的指令是定长的且均为 𝐿 字节（常见情况为 2/4 字节）。但是执行序列并不总是符合这种模式，当位于物理地址 𝑎𝑛 的指令是一条跳转指令的时候，该模式就有可能被破坏。跳转指令对应于我们在程序中构造的 **控制流** (Control Flow) 的多种不同结构，比如分支结构（如 if/switch 语句）和循环结构（如 for/while 语句）。用来实现上述两种结构的跳转指令，只需实现跳转功能，也就是将 pc 寄存器设置到一个指定的地址即可。

另一种控制流结构则显得更为复杂： **函数调用** (Function Call)。我们大概清楚调用函数整个过程中代码执行的顺序，如果是从源代码级的视角来看，我们会去执行被调用函数的代码，等到它返回之后，我们会回到调用函数对应语句的下一行继续执行。那么我们如何用汇编指令来实现这一过程？首先在调用的时候，需要有一条指令跳转到被调用函数的位置，这个看起来和其他控制结构没什么不同；但是在被调用函数返回的时候，我们却需要返回那条跳转过来的指令的下一条继续执行。这次用来返回的跳转究竟跳转到何处，在对应的函数调用发生之前是不知道的。比如，我们在两个不同的地方调用同一个函数，显然函数返回之后会回到不同的地址。这是一个很大的不同：其他控制流都只需要跳转到一个 *编译期固定下来* 的地址，而函数调用的返回跳转是跳转到一个 *运行时确定* （确切地说是在函数调用发生的时候）的地址。

<img src="https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/function-call.png" alt="../_images/function-call.png" style="zoom:80%;" />

对此，指令集必须给用于函数调用的跳转指令一些额外的能力，而不只是单纯的跳转。在 RISC-V 架构上，有两条指令即符合这样的特征：

| 指令                   | 指令功能           |
| ---------------------- | ------------------ |
| jal rd, imm[20:1]      | rd←pc+4; pc←pc+imm |
| jalr rd, (imm[11:0])rs | rd←pc+4; pc←rs+imm |

> 在大多数只与通用寄存器打交道的指令中， rs 表示 **源寄存器** (Source Register)， imm 表示 **立即数** (Immediate)，是一个常数，二者构成了指令的输入部分；而 rd 表示 **目标寄存器** (Destination Register)，它是指令的输出部分。rs 和 rd 可以在 32 个通用寄存器 x0~x31 中选取。但是这三个部分都不是必须的，某些指令只有一种输入类型，另一些指令则没有输出部分。

---

从中可以看出，这两条指令在设置 pc 寄存器完成跳转功能之前，还将当前跳转指令的下一条指令地址保存在 rd 寄存器中，即 rd←pc+4 这条指令的含义。（这里假设所有指令的长度均为 4 字节）在 RISC-V 架构中，通常使用 `ra` 寄存器（即 `x1` 寄存器）作为其中的 `rd` 对应的具体寄存器，因此在函数返回的时候，只需跳转回 `ra` 所保存的地址即可。事实上在函数返回的时候，我们常常使用一条 **汇编伪指令** (Pseudo Instruction) 跳转回调用之前的位置： `ret` 。它会被汇编器翻译为 `jalr x0, 0(x1)`，含义为跳转到寄存器 `ra` 保存的物理地址，由于 `x0` 是一个恒为 `0` 的寄存器，在 `rd` 中保存这一步被省略。

> 总结一下，在进行函数调用的时候，我们通过 `jalr` 指令保存返回地址并实现跳转；而在函数即将返回的时候，则通过 `ret` 伪指令，回到跳转之前的下一条指令继续执行。这样，RISC-V 的这两条指令就实现了函数调用流程的核心机制。

由于我们是在 `ra` 寄存器中保存返回地址的，我们要保证它在函数执行的全程不发生变化，不然在 `ret` 之后就会跳转到错误的位置。事实上，编译器除了函数调用的相关指令之外，确实基本上不使用 `ra` 寄存器。也就是说，如果在函数中没有调用其他函数，那 `ra` 的值不会变化，函数调用流程能够正常工作。但遗憾的是，在实际编写代码的时候我们常常会遇到函数 **多层嵌套调用** 的情形。我们很容易想象，如果函数不支持嵌套调用，那么编程将会变得多么复杂。如果我们试图在一个函数  𝑓  中调用一个子函数，在跳转到子函数 𝑔 的同时，ra 会被覆盖成这条跳转指令的下一条的地址，而 ra 之前所保存的函数  𝑓  的返回地址将会 永久丢失 。

因此，若想正确实现嵌套函数调用的控制流，我们必须通过某种方式保证：在一个函数调用子函数的前后，`ra` 寄存器的值不能发生变化。但实际上，这并不仅仅局限于 `ra` 一个寄存器，而是作用于所有的通用寄存器。这是因为，编译器是独立编译每个函数的，因此一个函数并不能知道它所调用的子函数修改了哪些寄存器。而站在一个函数的视角，在调用子函数的过程中某些寄存器的值被覆盖，的确会对它接下来的执行产生影响。因此这是必要的。

> 我们将由于函数调用，在控制流转移前后需要保持不变的寄存器集合称之为 **函数调用上下文** (Function Call Context) 。

---

由于每个 CPU 只有一套寄存器，我们若想在子函数调用前后，保持函数调用上下文不变，就需要物理内存的帮助。确切的说，在调用子函数之前，我们需要在物理内存中的一个区域 **保存** (Save) 函数调用上下文中的寄存器；而在函数执行完毕后，我们会从内存中同样的区域读取并 **恢复** (Restore) 函数调用上下文中的寄存器。实际上，这一工作是由子函数的调用者和被调用者（也就是子函数自身）合作完成。函数调用上下文中的寄存器被分为两类：

- **被调用者保存(Callee-Saved) 寄存器** ：被调用的函数可能会覆盖这些寄存器，需要被调用的函数来保存的寄存器，即由被调用的函数来保证在调用前后，这些寄存器保持不变；
- **调用者保存(Caller-Saved) 寄存器** ：被调用的函数可能会覆盖这些寄存器，需要发起调用的函数来保存的寄存器，即由发起调用的函数来保证在调用前后，这些寄存器保持不变。

从名字中可以看出，函数调用上下文由调用者和被调用者分别保存，其具体过程分别如下：

- **调用函数：**首先，保存不希望在函数调用过程中发生变化的 **调用者保存寄存器** ，然后通过 jal/jalr 指令调用子函数，返回之后恢复这些寄存器。
- **被调用函数：**在被调用函数的起始，先保存函数执行过程中被用到的 **被调用者保存寄存器** ，然后执行函数，最后在函数退出之前恢复这些寄存器。

我们发现，无论是调用函数还是被调用函数，都会因调用行为，而需要两段匹配的保存和恢复寄存器的汇编代码，可以分别将其称为 **开场** (Prologue) 和 **结尾** (Epilogue)，它们会由编译器帮我们自动插入，来完成相关寄存器的保存与恢复。一个函数既有可能作为调用者调用其他函数，也有可能作为被调用者被其他函数调用。

> **寄存器保存与编译器优化**
>
> 这里值得说明的是，调用者和被调用者实际上，只需分别按需保存调用者保存寄存器和被调用者保存寄存器的一个子集。对于调用函数而言，在调用子函数的时候，即使子函数修改了调用者保存寄存器，编译器在调用函数中插入的代码会恢复这些寄存器；而对于被调用函数而言，在其执行过程中没有使用到的被调用者保存寄存器也无需保存。编译器在进行后端代码生成时，知道在这两个场景中分别有哪些值得保存的寄存器。从这一角度也可以理解，*为何要将函数调用上下文分成两类：可以让编译器，尽可能早地优化掉一些无用的寄存器保存与恢复操作，提高程序的执行性能。*

---

#### calling convention

**调用规范** (Calling Convention) 约定在某个指令集架构上，某种编程语言的函数调用如何实现。它包括了:

1. 函数的输入参数和返回值如何传递；
2. 函数调用上下文中，调用者/被调用者保存寄存器的划分；
3. 其他的在函数调用流程中，对于寄存器的使用方法。

调用规范是对于一种确定的编程语言来说的，因为一般意义上的函数调用只会在编程语言的内部进行。当一种语言想要调用用另一门编程语言编写的函数接口时，编译器就需要同时清楚两门语言的调用规范，并对寄存器的使用做出调整。

> **RISC-V 架构上的 C 语言调用规范**
>
> RISC-V 架构上的 C 语言调用规范可以在 [这里](https://riscv.org/wp-content/uploads/2015/01/riscv-calling.pdf) 找到。 它对通用寄存器的使用做出了如下约定：
>
> | 寄存器组                  | 保存者       | 功能                                                     |
> | ------------------------- | ------------ | -------------------------------------------------------- |
> | a0~a7（ `x10~x17` ）      | 调用者保存   | 用来传递输入参数。其中的 a0 和 a1 还用来保存返回值。     |
> | t0~t6( `x5~x7,x28~x31` )  | 调用者保存   | 作为临时寄存器使用，在被调函数中可以随意使用无需保存。   |
> | s0~s11( `x8~x9,x18~x27` ) | 被调用者保存 | 作为临时寄存器使用，被调函数保存后才能在被调函数中使用。 |
>
> 剩下的 5 个通用寄存器情况如下：
>
> - zero( `x0` ) 之前提到过，它恒为零，函数调用不会对它产生影响；
> - ra( `x1` ) 是被调用者保存的。被调用者函数可能也会调用函数，在调用之前就需要修改 `ra` 使得这次调用能正确返回。因此，每个函数都需要在开头保存 `ra` 到自己的栈帧中，并在结尾使用 `ret` 返回之前将其恢复。栈帧是当前执行函数用于存储局部变量和函数返回信息的内存结构。
> - sp( `x2` ) 是被调用者保存的。这个是之后就会提到的栈指针 (Stack Pointer) 寄存器，它指向下一个将要被存储的栈顶位置。
> - fp( `s0` )，它既可作为s0临时寄存器，也可作为栈帧指针（Frame Pointer）寄存器，表示当前栈帧的起始位置，是一个被调用者保存寄存器。fp 指向的栈帧起始位置 和 sp 指向的栈帧的当前栈顶位置形成了所对应函数栈帧的空间范围。
> - gp( `x3` ) 和 tp( `x4` ) 在一个程序运行期间都不会变化，因此不必放在函数调用上下文中。它们的用途在后面的章节会提到。
>
> 更加详细的内容可以参考 Cornell 大学的 [CS 3410: Computer System Organization and Programming 课件内容](http://www.cs.cornell.edu/courses/cs3410/2019sp/schedule/slides/10-calling-notes-bw.pdf) 。

之前，我们讨论了函数调用上下文的保存/恢复时机以及寄存器的选择，但我们并没有详细说明这些寄存器保存在哪里，只是用“内存中的一块区域”草草带过。实际上，它更确切的名字是 **栈** (Stack) 。 `sp` 寄存器常用来保存 **栈指针** (Stack Pointer)，它指向内存中栈顶地址。

在 RISC-V 架构中，栈是从高地址向低地址增长的。在一个函数中，作为起始的开场代码负责分配一块新的栈空间，即将 `sp` 的值减小相应的字节数即可，于是物理地址区间 新旧[新sp,旧sp) 对应的物理内存的一部分，便可以被这个函数用来进行函数调用上下文的保存/恢复，这块物理内存被称为这个函数的 **栈帧** (Stack Frame)。同理，函数中的结尾代码负责将开场代码分配的栈帧回收，这也仅仅需要将 `sp` 的值增加相同的字节数，回到分配之前的状态。这也可以解释为什么 `sp` 是一个被调用者保存寄存器。

> **栈帧 stack frame**
>
> 我们知道程序在执行函数调用时，调用者函数和被调用函数使用的是同一个栈。在通常的情况下，我们并不需要区分调用者函数和被调用函数分别使用了栈的哪个部分。但是，当我们需要在执行过程中对函数调用进行调试或backtrace的时候，这一信息就很重要了。简单的说，栈帧（stack frame）就是一个函数所使用的栈的一部分区域，所有函数的栈帧串起来，就组成了一个完整的函数调用栈。一般而言，当前执行函数的栈帧的两个边界，分别由栈指针 (Stack Pointer)寄存器和栈帧指针（frame pointer）寄存器来限定。

如图所示，我们能够看到在程序依次调用 a、调用 b、调用 c、c 返回、b 返回整个过程中栈帧的分配/回收以及 `sp` 寄存器的变化。 图中标有 a/b/c 的块分别代表函数 a/b/c 的栈帧。

![../_images/CallStack.png](https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/CallStack.png)

> **数据结构中的栈与实现函数调用所需要的栈**
>
> 从数据结构的角度来看，栈是一个 **后入先出** (Last In First Out, LIFO) 的线性表，支持向栈顶压入一个元素以及从栈顶弹出一个元素两种操作，分别被称为 push 和 pop。从它提供的接口来看，它只支持访问栈顶附近的元素。因此在实现的时候，需要维护一个指向栈顶的指针来表示栈当前的状态。
>
> 我们这里的栈与数据结构中的栈原理相同，在很多方面可以一一对应。栈指针 `sp` 可以对应到指向栈顶的指针，对于栈帧的分配/回收可以分别对应到 `push` / `pop` 操作。如果将我们的栈看成一个内存分配器，它之所以可以这么简单，是因为它回收的内存一定是 *最近一次分配* 的内存，从而只需要类似 `push` / `pop` 的两种操作即可。

在合适的编译选项设置之下，一个函数的栈帧内容可能如下图所示：

![../_images/StackFrame.png](https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/StackFrame.png)

它的开头和结尾，分别在 sp(x2) 和 fp(s0) 所指向的地址。按照地址从高到低分别有以下内容，它们都是通过 `sp` 加上一个偏移量来访问的：

- `ra` 寄存器保存其返回之后的跳转地址，是一个被调用者保存寄存器；
- 父亲栈帧的结束地址 `fp` ，是一个被调用者保存寄存器；
- 其他被调用者保存寄存器 `s1` ~ `s11` ；
- 函数所使用到的局部变量。

因此，栈上多个 `fp` 信息实际上保存了一条完整的函数调用链，通过适当的方式我们可以实现对函数调用关系的跟踪。`ra` 、 `sp` 和 `fp` 是和函数调用紧密相关的寄存器，我们用一个例子来展示真实编译器生成的汇编代码会如何使用这些寄存器。

我们可以使用 `rust-objdump` 工具反汇编内核或者应用程序可执行文件，并找到某个函数的入口。然后，我们能够看到在函数的开场和结尾阶段，编译器会生成类似的汇编代码：

```assembly
# 开场
# 为当前函数分配 64 字节的栈帧
addi        sp, sp, -64
# 将 ra 和 fp 压栈保存
sd  ra, 56(sp)
sd  s0, 48(sp)
# 更新 fp 为当前函数栈帧顶端地址
addi        s0, sp, 64

# 函数执行
# 中间如果再调用了其他函数会修改 ra

# 结尾
# 恢复 ra 和 fp
ld  ra, 56(sp)
ld  s0, 48(sp)
# 退栈
addi        sp, sp, 64
# 返回，使用 ret 指令或其他等价的实现方式
ret
```

---

#### kernel boot stack

我们在 `entry.asm` 中分配启动栈空间，并在控制权被转交给 Rust 入口之前将栈指针 `sp` 设置为栈顶的位置。

```assembly
# os/src/entry.asm
    .section .text.entry
    .globl _start
_start:
    la sp, boot_stack_top
    call rust_main

    .section .bss.stack
    .globl boot_stack_lower_bound
boot_stack_lower_bound:
    .space 4096 * 16
    .globl boot_stack_top
boot_stack_top:
```

我们在第 11 行在内核的内存布局中预留了一块大小为 4096 * 16 字节也就是 64KiB 的空间，用作接下来要运行的程序的栈空间。在 RISC-V 架构上，栈是从高地址向低地址增长。因此，最开始的时候栈为空，栈顶和栈底位于相同的位置，我们用更高地址的符号 `boot_stack_top` 来标识栈顶的位置。同时，我们用更低地址的符号 `boot_stack_lower_bound` 来标识栈能够增长到的下限位置，它们都被设置为全局符号供其他目标文件使用。如下图所示：

![../_images/boot_stack.png](https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/boot_stack.png)

我们将这块空间放置在一个名为 `.bss.stack` 的段中，在链接脚本 `linker.ld` 中可以看到 `.bss.stack` 段最终会被汇集到 `.bss` 段中：

```assembly
.bss : {
    *(.bss.stack)
    sbss = .;
    *(.bss .bss.*)
    *(.sbss .sbss.*)
}
ebss = .;
```

回到 `entry.asm` ，可以发现在控制权转交给 Rust 入口之前会执行两条指令，它们分别位于 `entry.asm` 的第 5、6 行。第 5 行我们将栈指针 `sp` 设置为先前分配的启动栈栈顶地址，这样 Rust 代码在进行函数调用和返回的时候就可以正常在启动栈上分配和回收栈帧了。在我们设计好的内存布局中，这块启动栈所用的内存并不会和内核的其他代码、数据段产生冲突，它们是从物理上隔离的。然而如果启动栈溢出（比如在内核代码中出现了太多的函数调用），那么分配的栈帧将有可能覆盖内核其他部分的代码、数据从而出现十分诡异的错误。目前我们只能尽量避免栈溢出的情况发生 (借助地址空间抽象和 MMU 硬件的帮助，我们可以做到完全禁止栈溢出)。第 6 行我们通过伪指令 `call` 调用 Rust 编写的内核入口点 `rust_main` 将控制权转交给 Rust 代码，该入口点在 `main.rs` 中实现：

```rust
// os/src/main.rs
#[no_mangle]
pub fn rust_main() -> ! {
    loop {}
}
```

在 `rust_main` 函数的开场白中，我们将第一次在栈上分配栈帧并保存函数调用上下文，它也是内核运行全程中最底层的栈帧。

## 1.2 特权级切换

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter2/4trap-handling.html#id8

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter4/6multitasking-based-on-as.html

### 1) dis-mmu trap switch

#### TODO: 关于执行环境与控制流

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter0/3os-hw-abstract.html#term-exec-env-define

##### 执行环境



##### 普通控制流



##### 异常控制流



##### 控制流上下文 (执行环境的状态)







#### 关于特权切换

当执行一条 Trap 类指令（如 `ecall` 时），CPU 发现触发了一个异常并需要进行特殊处理，这涉及到 [执行环境切换](https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter0/3os-hw-abstract.html#term-ee-switch) 。

<img src="https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/complex-EE.png" alt="../_images/complex-EE.png" style="zoom:67%;" />

具体而言，用户态执行环境中的应用程序，通过 `ecall` 指令向内核态执行环境中的操作系统请求某项服务功能，那么处理器和操作系统会完成到内核态执行环境的切换，并在操作系统完成服务后，再次切换回用户态执行环境，然后应用程序会紧接着 `ecall` 指令的后一条指令位置处继续执行，参考 [图示](https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter2/1rv-privilege.html#environment-call-flow) 。

<img src="https://rcore-os.cn/rCore-Tutorial-Book-v3/_images/EnvironmentCallFlow.png" alt="../_images/EnvironmentCallFlow.png" style="zoom: 25%;" />

应用程序被切换回来之后，需要从发出系统调用请求的执行位置，恢复应用程序上下文并继续执行，这需要在切换前后维持应用程序的上下文保持不变。应用程序的上下文包括：通用寄存器和栈两个主要部分。由于 CPU 在不同特权级下共享一套通用寄存器，所以在运行操作系统的 Trap 处理过程中，操作系统也会用到这些寄存器，这会改变应用程序的上下文。因此，与函数调用需要保存函数调用上下文/活动记录一样，在执行操作系统的 Trap 处理过程（会修改通用寄存器）之前，我们需要在某个地方（某内存块或内核的栈）保存这些寄存器，并在 Trap 处理结束后恢复这些寄存器。

除了通用寄存器之外，还有一些可能在处理 Trap 过程中会被修改的 CSR，比如 CPU 所在的特权级。我们要保证它们的变化在我们的预期之内。比如，对于特权级转换而言，应该是 Trap 之前在 U 特权级，处理 Trap 的时候在 S 特权级，返回之后又需要回到 U 特权级。而对于栈问题则相对简单，只要两个应用程序执行过程中，用来记录执行历史的栈所对应的内存区域不相交，就不会产生令我们头痛的覆盖问题或数据破坏问题，也就无需进行保存/恢复。

特权级切换的具体过程一部分由硬件直接完成，另一部分则需要由操作系统来实现。

#### 硬件机制





#### 用户栈/内核栈





#### Trap上下文保存/恢复











### 2) en-mmu trap switch 







## 1.3 进程切换

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter3/2task-switching.html

https://rcore-os.cn/rCore-Tutorial-Book-v3/chapter5/2core-data-structures.html#idle

### 1) 任务切换





### 2) 任务调度的idle控制流







# TODO: 2 signal handle user-demo

https://gitee.com/aosp-riscv/working-group/blob/master/articles/20220816-signal-frame.md#/aosp-riscv/working-group/blob/master/articles/20220717-call-stack.md

## 2.1 信号的基本概念



## 2.2 信号处理与信号帧

### 1) linux-riscv trap in/out





### 2) trap handle with signal





## 2.3 signal-vector selftests

https://lore.kernel.org/all/20240403-vector_sigreturn_tests-v1-1-2e68b7a3b8d7@rivosinc.com/







# 3 linux-riscv signal handle support (fp/vector)

## 3.1 overview

```c
// arch/riscv/kernel/signal.c

unsigned long signal_minsigstksz __ro_after_init;

extern u32 __user_rt_sigreturn[2];
static size_t riscv_v_sc_size __ro_after_init;

#define DEBUG_SIG 0

struct rt_sigframe {
	struct siginfo info;
	struct ucontext uc;
#ifndef CONFIG_MMU
	u32 sigreturn_code[2];
#endif
};
```

```c
#ifdef CONFIG_FPU
static long restore_fp_state(struct pt_regs *regs,
			     union __riscv_fp_state __user *sc_fpregs);

static long save_fp_state(struct pt_regs *regs,
			  union __riscv_fp_state __user *sc_fpregs);
#else
#define save_fp_state(task, regs) (0)
#define restore_fp_state(task, regs) (0)
#endif

#ifdef CONFIG_RISCV_ISA_V
static long save_v_state(struct pt_regs *regs, void __user **sc_vec);
/*
 * Restore Vector extension context from the user's signal frame. This function
 * assumes a valid extension header. So magic and size checking must be done by
 * the caller.
 */
static long __restore_v_state(struct pt_regs *regs, void __user *sc_vec);
#else
#define save_v_state(task, regs) (0)
#define __restore_v_state(task, regs) (0)
#endif

static long restore_sigcontext(struct pt_regs *regs, struct sigcontext __user *sc);
static size_t get_rt_frame_size(bool cal_all);
SYSCALL_DEFINE0(rt_sigreturn);
static long setup_sigcontext(struct rt_sigframe __user *frame, struct pt_regs *regs);
static inline void __user *get_sigframe(struct ksignal *ksig, struct pt_regs *regs, size_t framesize);
static int setup_rt_frame(struct ksignal *ksig, sigset_t *set, struct pt_regs *regs);
static void handle_signal(struct ksignal *ksig, struct pt_regs *regs);

void arch_do_signal_or_restart(struct pt_regs *regs);
void init_rt_signal_env(void);
void __init init_rt_signal_env(void);

#ifdef CONFIG_DYNAMIC_SIGFRAME
bool sigaltstack_size_valid(size_t ss_size)
{
	return ss_size > get_rt_frame_size(false);
}
#endif /* CONFIG_DYNAMIC_SIGFRAME */
```

---

> **执行流分析**

```c
//linux-common处理流程
start_kernel
    +-> setup_arch(&command_line);
		+-> init_rt_signal_env();

//irqentry_exit_to_user_mode(struct pt_regs *regs)
do_trap_ecall_u(struct pt_regs *regs)
	+-> syscall_exit_to_user_mode(struct pt_regs *regs)
		+-> __syscall_exit_to_user_mode_work(struct pt_regs *regs)
			+-> exit_to_user_mode_prepare(regs);

/**
 * exit_to_user_mode_prepare - call exit_to_user_mode_loop() if required
 * @regs:	Pointer to pt_regs on entry stack
 *
 * 1) check that interrupts are disabled
 * 2) call tick_nohz_user_enter_prepare()
 * 3) call exit_to_user_mode_loop() if any flags from
 *    EXIT_TO_USER_MODE_WORK are set
 * 4) check that interrupts are still disabled
 */
exit_to_user_mode_prepare(struct pt_regs *regs)
    +-> ti_work = read_thread_flags();
		if (unlikely(ti_work & EXIT_TO_USER_MODE_WORK))
            /* exit_to_user_mode_loop - do any pending work before leaving to user space */
			exit_to_user_mode_loop(regs, ti_work);
            +-> if (ti_work & (_TIF_SIGPENDING | _TIF_NOTIFY_SIGNAL))
                   arch_do_signal_or_restart(regs);

//linux-riscv处理流程
arch_do_signal_or_restart(regs);
	+-> /* If we were from a system call, check for system call restarting */
        +-> //...
	+-> /*
	  	   Get the signal to deliver. When running under ptrace, at this point
	  	   the debugger may change all of our registers.
	 	*/
		if (get_signal(&ksig))
        +->  /* Actually deliver the signal */
			 handle_signal(&ksig, regs);
			 /* Set up the stack frame */
			 +-> setup_rt_frame(ksig, oldset, regs);
				 +-> frame = get_sigframe(ksig, regs, frame_size);
				 /* Create the ucontext. */
				 +-> setup_sigcontext(frame, regs);
					+-> /* Save the vector state. */
                        if (has_vector() && riscv_v_vstate_query(regs))
                            err |= save_v_state(regs, (void __user **)&sc_ext_ptr);
	+-> restore_saved_sigmask();

SYSCALL_DEFINE0(rt_sigreturn)
    +-> restore_sigcontext(regs, &frame->uc.uc_mcontext)
   		+-> void __user *sc_ext_ptr = &sc->sc_extdesc.hdr;
			sc_ext_ptr += sizeof(*head);
		/*
         * Restore Vector extension context from the user's signal frame. This function
         * assumes a valid extension header. So magic and size checking must be done by
         * the caller.
         */
    	+-> __restore_v_state(regs, sc_ext_ptr);
```





## 3.2 signal: linux-common





## 3.3 signal: linux-riscv





