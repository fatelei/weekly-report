#!/usr/bin/env python3
"""
Git Weekly Report Generator
根据最近一周的 git commit 生成周报
"""

import subprocess
import sys
import argparse
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union
import re
import requests


class LLMEnhancer:
    def __init__(self, api_key: Union[str, None] = None, model: str = "openai/gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def enhance_commit_message(self, message: str) -> str:
        """使用 LLM 翻译和润色 commit 消息"""
        if not self.api_key:
            return message
        
        prompt = f"""请将以下 git commit 消息翻译成中文，并进行适当的润色，使其更符合中文表达习惯。保持技术术语的准确性，让描述更加清晰易懂。

原始消息: {message}

请直接返回翻译润色后的中文消息，不要添加任何解释。"""
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/user/git-weekly-report",
                    "X-Title": "Git Weekly Report Generator"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 100
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"LLM API 调用失败: {response.status_code}")
                return message
                
        except Exception as e:
            print(f"LLM 调用出错: {e}")
            return message
    
    def generate_summary(self, commits: List[Dict[str, Any]]) -> str:
        """使用 LLM 生成工作总结"""
        if not self.api_key or not commits:
            return ""
        
        commit_texts = []
        for commit in commits[:10]:  # 限制数量避免 token 过多
            commit_texts.append(f"- {commit['author']}: {commit['message']}")
        
        prompt = f"""基于以下本周的 git commit 记录，请生成一段简洁的中文工作总结（50-100字），突出主要成果和进展：

{chr(10).join(commit_texts)}

请直接返回总结内容，不要添加任何标题或解释。"""
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/user/git-weekly-report",
                    "X-Title": "Git Weekly Report Generator"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 150
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return ""
                
        except Exception as e:
            print(f"LLM 总结生成出错: {e}")
            return ""


class GitWeeklyReport:
    def __init__(self, repo_path: str = ".", use_llm: bool = False, api_key: Union[str, None] = None, author: Union[str, None] = None):
        self.repo_path = repo_path
        self.use_llm = use_llm
        self.llm = LLMEnhancer(api_key) if use_llm else None
        self.author = author
        
    def get_commits_last_week(self) -> List[Dict[str, Any]]:
        """获取最近一周的 git commit"""
        one_week_ago = datetime.now() - timedelta(days=7)
        since_date = one_week_ago.strftime("%Y-%m-%d")
        
        try:
            # 获取 git log 信息
            cmd = [
                "git", "-C", self.repo_path, "log",
                f"--since={since_date}",
                "--pretty=format:%H|%an|%ad|%s",
                "--date=short",
                "--no-merges"
            ]
            
            # 如果指定了作者，添加作者过滤
            if self.author:
                cmd.append(f"--author={self.author}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            print(f"错误: 无法获取 git log 信息: {e}")
            return []
        except FileNotFoundError:
            print("错误: 未找到 git 命令，请确保已安装 git")
            return []
    
    def get_all_authors(self) -> List[str]:
        """获取仓库中所有作者列表"""
        try:
            cmd = [
                "git", "-C", self.repo_path, "log",
                "--pretty=format:%an",
                "--since=1.month ago",  # 最近一个月的作者
                "--no-merges",
                "|", "sort", "|", "uniq"
            ]
            
            # 使用 shell=True 来支持管道
            result = subprocess.run(
                " ".join(cmd), 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=True,
                cwd=self.repo_path
            )
            
            authors = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    authors.append(line.strip())
            
            return sorted(list(set(authors)))
            
        except subprocess.CalledProcessError:
            return []
    
    def get_commit_stats(self, commit_hash: str) -> Dict[str, int]:
        """获取单个 commit 的统计信息"""
        try:
            cmd = [
                "git", "-C", self.repo_path, "show",
                "--stat", "--format=", commit_hash
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            stats = {'files_changed': 0, 'insertions': 0, 'deletions': 0}
            
            # 解析统计信息
            for line in result.stdout.strip().split('\n'):
                if ' file' in line and 'changed' in line:
                    # 例如: " 5 files changed, 120 insertions(+), 30 deletions(-)"
                    match = re.search(r'(\d+)\s+file', line)
                    if match:
                        stats['files_changed'] = int(match.group(1))
                    
                    match = re.search(r'(\d+)\s+insertion', line)
                    if match:
                        stats['insertions'] = int(match.group(1))
                    
                    match = re.search(r'(\d+)\s+deletion', line)
                    if match:
                        stats['deletions'] = int(match.group(1))
            
            return stats
            
        except subprocess.CalledProcessError:
            return {'files_changed': 0, 'insertions': 0, 'deletions': 0}
    
    def enhance_commit_messages(self, commits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用 LLM 增强 commit 消息"""
        if not self.use_llm or not self.llm:
            return commits
        
        enhanced_commits = []
        for commit in commits:
            enhanced_commit = commit.copy()
            enhanced_commit['original_message'] = commit['message']
            enhanced_commit['message'] = self.llm.enhance_commit_message(commit['message'])
            enhanced_commits.append(enhanced_commit)
        
        return enhanced_commits
    
    def categorize_commits(self, commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将 commit 按类型分类"""
        categories = {
            '功能开发': [],
            'Bug修复': [],
            '文档更新': [],
            '代码优化': [],
            '测试相关': [],
            '其他': []
        }
        
        for commit in commits:
            message = commit['message'].lower()
            
            if any(keyword in message for keyword in ['feat', 'feature', 'add', '新增', '添加', 'implement', 'create']):
                categories['功能开发'].append(commit)
            elif any(keyword in message for keyword in ['fix', 'bug', '修复', '解决', 'patch', 'resolve']):
                categories['Bug修复'].append(commit)
            elif any(keyword in message for keyword in ['doc', 'readme', '文档', '说明', 'update', 'changelog']):
                categories['文档更新'].append(commit)
            elif any(keyword in message for keyword in ['refactor', 'optimize', '优化', '重构', 'improve', 'enhance']):
                categories['代码优化'].append(commit)
            elif any(keyword in message for keyword in ['test', '测试', 'spec', 'unit', 'coverage']):
                categories['测试相关'].append(commit)
            else:
                categories['其他'].append(commit)
        
        return categories
    
    def generate_report(self, commits: List[Dict[str, Any]]) -> str:
        """生成周报"""
        if not commits:
            if self.author:
                return f"# 本周工作周报 - {self.author}\n\n本周暂无代码提交记录。\n"
            else:
                return "# 本周工作周报\n\n本周暂无代码提交记录。\n"
        
        # 使用 LLM 增强 commit 消息
        if self.use_llm:
            print("正在使用 LLM 优化 commit 消息...")
            commits = self.enhance_commit_messages(commits)
        
        # 按日期分组
        commits_by_date = {}
        for commit in commits:
            date = commit['date']
            if date not in commits_by_date:
                commits_by_date[date] = []
            commits_by_date[date].append(commit)
        
        # 按类型分类
        categorized = self.categorize_commits(commits)
        
        # 统计信息
        total_commits = len(commits)
        total_files = 0
        total_insertions = 0
        total_deletions = 0
        
        for commit in commits:
            stats = self.get_commit_stats(commit['hash'])
            total_files += stats['files_changed']
            total_insertions += stats['insertions']
            total_deletions += stats['deletions']
        
        # 生成报告
        report = []
        if self.author:
            report.append(f"# 本周工作周报 - {self.author}")
        else:
            report.append("# 本周工作周报")
        report.append("")
        report.append(f"**统计时间**: {commits[0]['date']} ~ {commits[-1]['date']}")
        report.append("")
        
        # LLM 生成的工作总结
        if self.use_llm and self.llm:
            print("正在生成工作总结...")
            summary = self.llm.generate_summary(commits)
            if summary:
                report.append("## 🎯 本周总结")
                report.append("")
                report.append(summary)
                report.append("")
        
        # 统计概览
        report.append("## 📊 统计概览")
        report.append("")
        report.append(f"- **提交次数**: {total_commits} 次")
        report.append(f"- **文件变更**: {total_files} 个文件")
        report.append(f"- **代码新增**: +{total_insertions} 行")
        report.append(f"- **代码删除**: -{total_deletions} 行")
        report.append("")
        
        # 按类型展示
        report.append("## 📋 工作分类")
        report.append("")
        
        for category, category_commits in categorized.items():
            if category_commits:
                report.append(f"### {category} ({len(category_commits)})")
                for commit in category_commits:
                    # 如果有原始消息，显示对比
                    if self.use_llm and 'original_message' in commit:
                        report.append(f"- **{commit['author']}**: {commit['message']}")
                        report.append(f"  *原始*: {commit['original_message']}")
                    else:
                        report.append(f"- **{commit['author']}**: {commit['message']}")
                report.append("")
        
        # 按日期展示
        report.append("## 📅 每日详情")
        report.append("")
        
        for date in sorted(commits_by_date.keys(), reverse=True):
            date_commits = commits_by_date[date]
            report.append(f"### {date}")
            for commit in date_commits:
                stats = self.get_commit_stats(commit['hash'])
                stats_str = f"({stats['files_changed']} 文件, +{stats['insertions']}/-{stats['deletions']})"
                report.append(f"- **{commit['author']}** {stats_str}: {commit['message']}")
            report.append("")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Git 周报生成工具")
    parser.add_argument("--repo", "-r", default=".", help="Git 仓库路径 (默认: 当前目录)")
    parser.add_argument("--output", "-o", help="输出文件路径 (默认: 输出到控制台)")
    parser.add_argument("--use-llm", action="store_true", help="使用 LLM 增强周报内容")
    parser.add_argument("--api-key", help="OpenRouter API Key (也可通过环境变量 OPENROUTER_API_KEY 设置)")
    parser.add_argument("--model", default="openai/gpt-3.5-turbo", help="LLM 模型 (默认: openai/gpt-3.5-turbo)")
    parser.add_argument("--author", "-a", help="指定作者姓名，只生成该作者的周报")
    parser.add_argument("--list-authors", action="store_true", help="列出仓库中所有作者")
    
    args = parser.parse_args()
    
    # 创建周报生成器
    generator = GitWeeklyReport(
        repo_path=args.repo,
        use_llm=args.use_llm,
        api_key=args.api_key,
        author=args.author
    )
    
    # 如果要求列出作者
    if args.list_authors:
        authors = generator.get_all_authors()
        if authors:
            print("仓库中的作者列表:")
            for i, author in enumerate(authors, 1):
                print(f"  {i}. {author}")
        else:
            print("未找到作者信息")
        return
    
    # 如果使用 LLM，检查 API Key
    if args.use_llm:
        api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("错误: 使用 LLM 功能需要提供 OpenRouter API Key")
            print("请通过 --api-key 参数或环境变量 OPENROUTER_API_KEY 设置")
            return
        print(f"使用 LLM 模型: {args.model}")
    
    # 获取最近一周的提交
    if args.author:
        print(f"正在获取作者 '{args.author}' 最近一周的 git commit...")
    else:
        print("正在获取最近一周的 git commit...")
    
    commits = generator.get_commits_last_week()
    
    if not commits:
        if args.author:
            print(f"未找到作者 '{args.author}' 最近一周的提交记录")
        else:
            print("未找到最近一周的提交记录")
        return
    
    if args.author:
        print(f"找到作者 '{args.author}' 的 {len(commits)} 条提交记录")
    else:
        print(f"找到 {len(commits)} 条提交记录")
    
    # 生成报告
    print("正在生成周报...")
    report = generator.generate_report(commits)
    
    # 输出报告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"周报已保存到: {args.output}")
    else:
        print("\n" + "="*50)
        print(report)


if __name__ == "__main__":
    main()