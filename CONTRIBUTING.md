# 贡献指南

感谢您对 Video Workshop 的关注！我们欢迎任何形式的贡献，包括但不限于：

## 贡献方式

### 报告 Bug

1. 使用 GitHub Issues 提交
2. 请包含以下信息：
   - 运行环境（操作系统、Python 版本）
   - 完整的错误日志
   - 复现步骤
   - 预期行为与实际行为

### 提交功能建议

- 清晰地描述你希望的功能
- 解释该功能的使用场景
- 如果可能，提供实现思路

### 提交代码

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 提交信息使用 Conventional Commits 格式
- 新增功能需包含对应的测试用例
- 确保所有测试通过：`python video_gen/tests/run_all.py`

### 开发流程

1. 确保已安装所有依赖：`pip install -r requirements.txt`
2. 在 `video_gen/` 目录下开发，保持与原有代码隔离
3. 运行测试确保不破坏现有功能
4. 更新文档（如适用）

## 行为准则

- 保持友善和尊重
- 接受建设性的批评
- 关注于技术本身

## 联系方式

如有任何问题，请通过 GitHub Issues 与我们联系。