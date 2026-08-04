![New Music Builder](docs/images/NewMusicBuilder-640-transparent.png)

# New Music Builder（新音乐构建器）

New Music Builder 是 [Tali's New Music](https://steamcommunity.com/sharedfiles/filedetails/?id=3739256725) 的配套制作工具。

它专为《Project Zomboid》（僵尸毁灭工程）的模组作者打造，让你又快又省心地搞定多轨音乐介质——告别手搓配置文件，导出时也少走弯路、少踩坑。

## 它能干啥

New Music Builder 帮你一站式拼装出可直接上传工坊的音乐包，支持：

- 多轨卡带、黑胶、CD 介质搭建
- 以"行"为单位管理媒体：展开/折叠、拖拽排序、逐行管理歌曲
- 封面与外观选择：卡带、卡带盒、黑胶、唱片套、CD 封面素材一网打尽
- 自动从封面生成卡带/卡带盒/黑胶/唱片套/CD 封面的纹理
- 音频转码与压缩
- 创作过程中的预览与整理工具
- 工坊海报预览与导出
- 直接导出为 Project Zomboid 模组/工坊文件夹结构

## 关于这个软件

如果你想给 Tali's New Music 制作自定义音乐介质，又不想手写一堆配套文件，用它就对了。
它天生就是为"多轨歌曲 + 多种介质外观需要统一管理"的音乐包场景而生的。

## 版本

当前版本：`0.4.3`

本版本重点在于让混合「合辑」（Mixtape）与「单曲」（Singles）音乐包的规模化导出更干净，让超大曲库也能保持高速导出，并稳住了上千首歌曲工程的导出队列与生成预览流程。

亮点一览：

- 针对大型音乐包优化了模块 2、模块 4、模块 5 的操作体验
- 并行转码数量受限，导出吞吐更快，日志刷屏更温和
- 高强度构建下 `.ogg` 直通与中止响应更跟手
- 旧版模式（Legacy Mode）从"全局开关"改为逐行切换「合辑」/「单曲」
- 支持混合音乐包——两种行类型可以在同一次导出中共存

## 平台支持

- Windows 是官方打包发布的主平台。
- Linux 和 macOS 理论上可直接用 Python 3.12+ 从源码运行。
- 代码层面尽量保持跨平台，但 Windows 仍是第一优先级的发布环境。

## Windows 打包版说明

Windows 下载版是一个未签名的 Python 桌面应用打包程序。

也就是说，就算安装包本身干净，部分杀毒软件仍可能因为它带着 Python 运行时、原生 DLL 和应用资源一起发布，而弹出启发式警告。

为了尽可能减少误报，打包版做了以下努力：

- 运行时状态在首次启动时才创建，放在 `%LOCALAPPDATA%\NewMusicBuilder` 下
- 随附目录只保留可执行文件和必要的运行时文件
- 发布压缩包里不必要的打包残留一律清理掉

如果你对打包版 exe 不太放心，也可以走下面的源码手动运行路线。

## 当前状态

- 歌曲包导出已全链路跑通。
- 卡带、卡带盒、黑胶、唱片套、CD 封面介质的自动纹理生成已就位。
- 封面、压缩、命名、整理、Lua/引导文件输出、工坊海报输出、纹理导出均已就位。
- 项目目前处于打磨收尾、稳定发布的阶段，而不是大刀阔斧改功能。

## 从源码运行

### Linux / macOS

在仓库目录下执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

如果没装 `python3.12`，先用你的包管理器装一个。

如果提示缺少 `tkinter`，装上发行版的 Tk 包再试一次。

### Windows

在仓库目录下执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

如果双击 `main.py` 只是闪一下就没了，改用 `Launch New Music Builder.bat` 启动，这样启动报错能留在屏幕上看得见。

## 仓库说明

- `src/new_music_builder/`：应用源码。
- `assets/`：运行时资源。
- `workspace/`、`logs/`、`Generated Textures/`：源码运行时的状态/数据目录，不算源码内容。
- Windows 打包版会在 `%LOCALAPPDATA%\NewMusicBuilder` 下创建运行时状态。
- `_references/` 不进 Git，也不属于公开源码分发的一部分。

## 版权与许可

Copyright © 2026 Talismon. 保留所有权利。

本仓库仅用于确立作者身份与开发历史。
未经明确书面许可，本项目的任何部分均不得复制、再分发、重新上传、修改发布，或并入其他应用、模组、工具或项目。

完整条款见 [LICENSE.md](LICENSE.md)。
