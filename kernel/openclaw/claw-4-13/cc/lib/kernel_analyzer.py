"""
内核分析工具 - 用于分析RISC-V vs ARM/x86内核代码差异
"""
import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class FeatureGap:
    """功能差距"""
    name: str
    category: str
    arm_x86_status: str
    riscv_status: str
    priority: str
    impact: str
    files: List[str]
    missing_functions: List[str]


@dataclass
class AnalysisResult:
    """分析结果"""
    dimension: str
    gaps: List[FeatureGap]
    summary: str
    recommendations: List[str]


class KernelAnalyzer:
    """内核分析器"""

    def __init__(self, linux_repo_path: str = None):
        self.linux_repo_path = linux_repo_path or os.environ.get(
            'LINUX_REPO_PATH',
            os.path.expanduser('~/linux')
        )
        self.riscv_path = os.path.join(self.linux_repo_path, 'arch', 'riscv')
        self.arm_path = os.path.join(self.linux_repo_path, 'arch', 'arm')
        self.x86_path = os.path.join(self.linux_repo_path, 'arch', 'x86')

    def analyze_kvm_support(self) -> AnalysisResult:
        """分析KVM支持差异"""
        gaps = []

        # 检查KVM目录结构
        riscv_kvm = os.path.join(self.riscv_path, 'kvm')
        arm_kvm = os.path.join(self.arm_path, 'kvm')
        x86_kvm = os.path.join(self.x86_path, 'kvm')

        # 读取现有文件
        riscv_files = self._get_c_files(riscv_kvm)
        arm_files = self._get_c_files(arm_kvm)
        x86_files = self._get_c_files(x86_kvm)

        # 分析缺失的功能
        if not os.path.exists(os.path.join(riscv_kvm, 'mmu.c')):
            gaps.append(FeatureGap(
                name='KVM MMU管理',
                category='kvm_support',
                arm_x86_status='已实现完整的MMU管理，包括EPT/NPT支持',
                riscv_status='基础实现，缺少Sv39/Sv48/Sv57完整支持',
                priority='P0',
                impact='影响内存虚拟化性能和安全性',
                files=['arch/riscv/kvm/mmu.c'],
                missing_functions=['kvm_init_shadow', 'kvm_shadow_map', 'kvm_s2_translate']
            ))

        if not os.path.exists(os.path.join(riscv_kvm, 'aia.c')):
            gaps.append(FeatureGap(
                name='高级中断控制器(AIA)支持',
                category='virtualization_features',
                arm_x86_status='支持GICv3/v4完整虚拟化',
                riscv_status='AIA支持不完整，缺少IMSIC虚拟化',
                priority='P1',
                impact='影响中断处理性能和实时性',
                files=['arch/riscv/kvm/aia.c'],
                missing_functions=['kvm_riscv_aia_init', 'kvm_riscv_vcpu_aia_init']
            ))

        # 检查调试支持
        riscv_debug = os.path.join(riscv_kvm, 'debug.c')
        if not os.path.exists(riscv_debug):
            gaps.append(FeatureGap(
                name='KVM调试支持',
                category='processor_features',
                arm_x86_status='支持完整的调试架构，包括硬件断点',
                riscv_status='缺少硬件断点/watchpoint支持',
                priority='P1',
                impact='影响调试和分析工具的可用性',
                files=['arch/riscv/kvm/debug.c'],
                missing_functions=['kvm_riscv_set_breakpoint', 'kvm_riscv_set_watchpoint']
            ))

        # 检查性能监控
        riscv_pmu = os.path.join(riscv_kvm, 'pmu.c')
        if not os.path.exists(riscv_pmu):
            gaps.append(FeatureGap(
                name='PMU虚拟化',
                category='processor_features',
                arm_x86_status='支持完整的PMU虚拟化，包括硬件事件',
                riscv_status='缺少PMU虚拟化支持',
                priority='P2',
                impact='影响性能分析和调优工具',
                files=['arch/riscv/kvm/pmu.c'],
                missing_functions=['kvm_riscv_pmu_init', 'kvm_riscv_pmu_vcpu_init']
            ))

        return AnalysisResult(
            dimension='kvm_support',
            gaps=gaps,
            summary=f'发现{len(gaps)}个KVM支持差距',
            recommendations=self._generate_recommendations(gaps)
        )

    def analyze_processor_features(self) -> AnalysisResult:
        """分析处理器特性支持差异"""
        gaps = []

        # Vector扩展支持
        riscv_vlen = self._check_vector_support()
        if not riscv_vlen:
            gaps.append(FeatureGap(
                name='Vector扩展支持',
                category='processor_features',
                arm_x86_status='支持SVE/SME，允许可变向量长度',
                riscv_status='RVV 1.0支持，但缺少动态向量长度适配',
                priority='P1',
                impact='影响向量计算性能和兼容性',
                files=['arch/riscv/kvm/vcpu_vector.c'],
                missing_functions=['kvm_riscv_vcpu_set_vector', 'kvm_riscv_vcpu_get_vector']
            ))

        # 检查TLB管理
        gaps.append(FeatureGap(
            name='TLB shootdown优化',
            category='performance',
            arm_x86_status='支持异步TLB shootdown和IPI批处理',
            riscv_status='缺少优化的TLB flush机制',
            priority='P1',
            impact='影响多核虚拟化性能',
            files=['arch/riscv/kvm/tlb.c'],
            missing_functions=['kvm_riscv_tlb_flush_range', 'kvm_riscv_tlb_shootdown']
        ))

        return AnalysisResult(
            dimension='processor_features',
            gaps=gaps,
            summary=f'发现{len(gaps)}个处理器特性差距',
            recommendations=self._generate_recommendations(gaps)
        )

    def analyze_virtualization_features(self) -> AnalysisResult:
        """分析虚拟化特性差异"""
        gaps = []

        # 嵌套虚拟化
        gaps.append(FeatureGap(
            name='嵌套虚拟化',
            category='virtualization_features',
            arm_x86_status='支持完整的两级虚拟化架构',
            riscv_status='缺少嵌套虚拟化(RISC-V Hypervisor扩展)支持',
            priority='P2',
            impact='影响虚拟化测试和分层部署',
            files=['arch/riscv/kvm/nested.c'],
            missing_functions=['kvm_riscv_nested_init', 'kvm_riscv_vcpu_nested_run']
        ))

        return AnalysisResult(
            dimension='virtualization_features',
            gaps=gaps,
            summary=f'发现{len(gaps)}个虚拟化特性差距',
            recommendations=self._generate_recommendations(gaps)
        )

    def analyze_all(self) -> List[AnalysisResult]:
        """执行完整分析"""
        return [
            self.analyze_kvm_support(),
            self.analyze_processor_features(),
            self.analyze_virtualization_features()
        ]

    def _get_c_files(self, directory: str) -> List[str]:
        """获取目录下的C文件"""
        if not os.path.exists(directory):
            return []
        return [f for f in os.listdir(directory) if f.endswith('.c')]

    def _check_vector_support(self) -> bool:
        """检查Vector支持"""
        vcpu_vector = os.path.join(self.riscv_path, 'kvm', 'vcpu_vector.c')
        return os.path.exists(vcpu_vector)

    def _generate_recommendations(self, gaps: List[FeatureGap]) -> List[str]:
        """生成建议"""
        recommendations = []
        for gap in gaps:
            if gap.priority == 'P0':
                recommendations.append(f'[紧急] 优先实现{gap.name}')
            elif gap.priority == 'P1':
                recommendations.append(f'[重要] 规划实现{gap.name}')
            else:
                recommendations.append(f'[优化] 考虑实现{gap.name}')
        return recommendations


# 分析结果导出
def export_gap_report(results: List[AnalysisResult], output_path: str):
    """导出差距报告"""
    import json

    report = {
        'timestamp': subprocess.run(
            ['date', '+%Y-%m-%d %H:%M:%S'],
            capture_output=True,
            text=True
        ).stdout.strip(),
        'results': [
            {
                'dimension': r.dimension,
                'summary': r.summary,
                'gaps': [
                    {
                        'name': g.name,
                        'category': g.category,
                        'arm_x86_status': g.arm_x86_status,
                        'riscv_status': g.riscv_status,
                        'priority': g.priority,
                        'impact': g.impact,
                        'files': g.files,
                        'missing_functions': g.missing_functions
                    }
                    for g in r.gaps
                ],
                'recommendations': r.recommendations
            }
            for r in results
        ]
    }

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
