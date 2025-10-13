# 查看仓库中所有作者
python3 git-weekly-report.py --list-authors

# 生成指定作者的周报
python3 git-weekly-report.py --author "张三"

# 结合 LLM 使用
python3 git-weekly-report.py --author "张三" --use-llm

# 保存到文件
python3 git-weekly-report.py --author "张三" --output zhangsan-weekly.md

