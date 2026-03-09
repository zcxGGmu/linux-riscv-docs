# 【BibiGPT】AI 一键总结：[精通OpenClaw变高手，OpenClaw从中级到高级完整教程](https://bibigpt.co/video/BV1ZiNwzPEhP)

![](https://i1.hdslb.com/bfs/archive/cbd68a4bbc1f83e4b5f35628192be859d55a1d9a.jpg)


## 摘要  
本视频是OpenClaw从中级到高级的完整教程，涵盖记忆系统、网络搜索修复、云服务器部署、个人微信/飞书插件接入、多Agent功能配置及心跳机制等核心内容。视频详细演示了OpenClaw的安装升级流程、Skills市场的高效用法（如修复搜索功能）、多Agent分身创建，以及通过企业微信实现合规的微信接入方案。最后对比了心跳与定时任务的差异，并提供了云服务器部署的实操指南。


### 亮点  
- 🧠 **记忆系统解析**：OpenClaw通过`agents.md`等文件存储工作规范、自我认知和长期记忆，用户可手动修改纠正AI行为 [05:17]  
- 🔍 **搜索功能修复**：通过安装`Web Search`和`Multi Search Engine`两个Skills，替代原生Brave API依赖，实现稳定联网搜索 [12:45]  
- 🤖 **多Agent实战**：演示创建"林黛玉"分身，独立配置性格/记忆文件夹，并绑定不同飞书账号实现差异化服务 [32:10]  
- ⏱️ **心跳机制**：对比定时任务，心跳具备完整对话历史，适合情感维系等复杂任务，案例演示每小时自动推送金价 [25:30]  
- ☁️ **云服务器部署**：国内Linux服务器安装指南，通过SSH隧道访问无桌面环境的OpenClaw，解决企业微信公网IP需求 [45:20]  


[#OpenClaw进阶](https://bibigpt.co/search?q=OpenClaw%E8%BF%9B%E9%98%B6) [#AI技能扩展](https://bibigpt.co/search?q=AI%E6%8A%80%E8%83%BD%E6%89%A9%E5%B1%95) [#多Agent开发](https://bibigpt.co/search?q=%E5%A4%9AAgent%E5%BC%80%E5%8F%91)  


### 思考  
1. **[如何避免Skills市场的恶意程序风险？](https://bibigpt.co/search?q=%E5%A6%82%E4%BD%95%E9%81%BF%E5%85%8DSkills%E5%B8%82%E5%9C%BA%E7%9A%84%E6%81%B6%E6%84%8F%E7%A8%8B%E5%BA%8F%E9%A3%8E%E9%99%A9%EF%BC%9F)**  
   - 优先选择Star数高的Skills，禁用自动安装功能（如`Find Skill`），人工审核代码后再部署。  
- 2. **[心跳与定时任务的核心区别是什么？](https://bibigpt.co/search?q=%E5%BF%83%E8%B7%B3%E4%B8%8E%E5%AE%9A%E6%97%B6%E4%BB%BB%E5%8A%A1%E7%9A%84%E6%A0%B8%E5%BF%83%E5%8C%BA%E5%88%AB%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F)**  
   - 心跳有完整对话上下文，适合复杂任务；定时任务独立执行，适合精确简单操作（如提醒）。  


### 术语解释  
- **Skills**：OpenClaw的功能扩展包，通过安装Skills（如搜索/总结工具）快速赋予AI新能力。  
- **Agent**：指独立的AI机器人实例，多Agent功能允许同一环境运行多个不同配置的AI分身。  
- **Coding Plan**：按调用次数计费的AI模型服务方案，适合OpenClaw的高Token消耗场景。

---

## 视频章节总结 ｜ OpenClaw进阶大师课：从零到高阶部署，全方位掌握搜索、记忆、多Agent与微信接入

本视频是一份深度进阶指南，旨在帮助OpenClaw用户从入门迈向高手。教程涵盖了记忆系统解析、联网搜索功能修复、多Agent系统部署及接入飞书与个人微信等核心模块。通过精选Skills市场应用、自定义配置文件及云服务器实战部署，详细展示了如何拓展AI的能力边界。无论是通过心跳机制实现自动化任务管理，还是利用多Agent架构配置不同性格的虚拟助手，本教程都提供了实操路径，极大地增强了OpenClaw的实用性与可玩性，是提升AI效率与个性化配置的必备宝典。

### [00:00](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=0.000) - 🛠️ OpenClaw安装与进阶设置

![章节截图 00:00](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/0.jpg)

本章重点回顾了OpenClaw在macOS环境下的基础安装流程，包括Node.js环境搭建与初始化配置。作者强调了修改配置文件中‘role’权限的重要性，指出若不开启所有工具调用权限，AI将无法执行具体操作。此外，通过配置Coding Plan代替普通Token计费，可以有效优化使用成本。完成这些初始设置后，AI将拥有更广泛的执行能力，为后续接入高级功能打下基础。

### [02:09](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=129.000) - 🧠 核心记忆系统深度拆解

![章节截图 02:09](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/129.jpg)

深入探讨了OpenClaw工作目录下的关键Markdown文件，这些文件构成了AI的‘大脑’与‘灵魂’。其中agents.md定义工作规范，identity.md保存自我认知，user.md与tools.md分别记录用户偏好与工具调用知识。此外，memory.md管理长期记忆，而heartbeat.md则涉及心跳机制，允许用户通过直接修改这些文件来纠正AI的行为，从而实现更精准的个性化交互。

### [03:01](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=181.000) - 🔍 修复并增强联网搜索能力

![章节截图 03:01](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/181.jpg)

针对原生搜索功能缺失的问题，本章展示了通过安装Web Search与Multi Search Engine等Skills进行修复的方案。作者详细介绍了获取API Key的方法，并通过修改配置文件及提示词，引导AI优先调用指定的搜索工具。这种方案不仅不需要复杂的配置，还能利用多个搜索引擎获取更全面的信息，通过Skills重构使得AI的联网能力得到了显著提升。

### [05:54](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=354.000) - 📦 玩转Skills扩展AI技能

![章节截图 05:54](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/354.jpg)

介绍了寻找与安装Skills的三种主要途径：内置Skills、官方CloudHub市场以及GitHub开源库。作者展示了如何安装诸如Apple Reminder、Summarize等实用插件，并强调了在安装过程中需注意安全，优先选择高星项目。通过演示将PDF文档总结技能接入AI的过程，说明了如何通过环境变量配置API Key，使AI能够快速掌握处理文档、金融分析等专业能力。

### [08:48](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=528.000) - 💬 接入飞书与多Agent部署

![章节截图 08:48](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/528.jpg)

本章深入讲解了OpenClaw接入飞书的详细流程，从企业自建应用创建到权限配置与事件订阅，实现了机器人与AI的联动。同时引入了‘多Agent’架构，展示了如何在同一系统中创建多个性格迥异的机器人分身。通过配置不同的工作区与频道绑定，用户可以同时拥有多个独立的AI助手，极大拓展了AI的应用场景，满足不同任务需求。

### [14:47](https://bibigpt.co/content/08e9ce61-b0f3-4f33-a61c-22784b3b7b86?t=887.000) - 🤖 云服务器部署与微信接入

![章节截图 14:47](https://bibigpt-apps.chatvid.ai/screenshots/bilibili.com/BV1ZiNwzPEhP/887.jpg)

为了实现个人微信的接入，本章重点演示了在Linux云服务器上部署OpenClaw的方案。通过SSH隧道连接服务器，利用企业微信机器人作为合规中转，解决了公网访问的痛点。教程详细指导了端口放行、接收消息API配置及企业微信后台的各项授权操作，最终成功实现了通过个人微信与远程服务器上的AI机器人进行稳定对话，完成了闭环部署。