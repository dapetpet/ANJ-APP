# ANJ-APP
按键精灵

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 打包（生成可直接运行的 exe）

在包含 main.py 的目录执行：

```bash
pyinstaller --noconsole --onefile --name AutoKey main.py
```

输出位置：

- `dist/AutoKey.exe`（使用了 `--onefile` 时）
- 如果你只执行了 `pyinstaller main.py`（没加 `--onefile`），通常会是 `dist/main/main.exe`

## 一键下载（推荐）

把本仓库推到 GitHub 后，启用 Actions，会自动生成 Windows 产物并提供下载：

- 工作流文件：`.github/workflows/windows-build.yml`
- 产物：`AutoKey.exe`（Actions 的 Artifacts 下载）
