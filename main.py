import os
import requests
from bs4 import BeautifulSoup
import gradio as gr
from volcenginesdkarkruntime import Ark
import feedparser
import yaml
from datetime import datetime
from logger import LOG
from jiqizhixin_client import JiqizhixinClient


DEFAULT_MODEL_TYPE = "doubao"

# 初始化 Ark 客户端
client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    timeout=120,
    max_retries=2,
)

# 定义一个函数来收集 feeds 信息源的内容
def collect_feeds(feed_urls):
    news_content = ""
    for url in feed_urls:
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        for entry in feed.entries:
            news_content += entry.summary + "\n"
    return news_content

def load_models_from_yaml():
    with open("models.yaml", "r") as file:
        return yaml.safe_load(file)

def create_model_choices(model_type):
    models = load_models_from_yaml()
    if models and model_type in models:
        choices = {
            model_name: model_config['id']
            for model_name, model_config in models[model_type].items()
        }
        return choices
    return {}

def update_model_name_list(model_type):
    choices = create_model_choices(model_type)
    return gr.Dropdown(
        choices=choices,
        label="选择模型",
        value=list(choices.keys())[0] if choices else None
    )

def get_default_model_name_list():
    choices = create_model_choices(DEFAULT_MODEL_TYPE)
    default_value = list(choices.keys())[0] if choices else None
    # 获取默认选择的模型ID
    default_model_id = None
    if default_value:
        models = load_models_from_yaml()
        default_model_id = models[DEFAULT_MODEL_TYPE][default_value]['id']
    
    return [
        gr.Dropdown(
            choices=choices,
            label="选择模型",
            value=default_value
        ),
        default_model_id  # 返回默认模型ID
    ]

def on_model_select(choice):
    if not choice:  # 如果没有选择，返回空字符串
        return ""
    # 获取选择的模型名称对应的ID
    models = load_models_from_yaml()
    model_id = models[DEFAULT_MODEL_TYPE][choice]['id']
    return model_id

def generate_jixiezhixin_topic(model_type, model_name):
    try:
        # 获取当前时间
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_hour = datetime.now().strftime('%H')
        
        # 初始化客户端
        ph_client = JiqizhixinClient()
        
        # 获取内容
        md_file_path = ph_client.export_articles(current_date, current_hour)
        
        if not md_file_path or not os.path.exists(md_file_path):
            LOG.error("无法获取内容或文件不存在")
            return "无法获取内容，请稍后重试", None
            
        # 读取文件内容并进行预处理
        try:
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                
            if not content:
                LOG.error("文件内容为空")
                return "获取到的内容为空，请稍后重试", None
                
        except Exception as e:
            LOG.error(f"读取文件失败: {str(e)}")
            return f"读取内容失败: {str(e)}", None
            
        # 获取模型配置
        try:
            models = load_models_from_yaml()
            if model_type not in models or model_name not in models[model_type]:
                LOG.error(f"无效的模型配置: {model_type}/{model_name}")
                return "无效的模型配置", None
                
            model_id = models[model_type][model_name]['id']
        except Exception as e:
            LOG.error(f"获取模型配置失败: {str(e)}")
            return f"获取模型配置失败: {str(e)}", None
        
        # 构建更详细的 prompt
        prompt = f"""请仔细阅读以下内容，并按照要求进行分析：

1. 产品分类分析：
   - 按照产品类型进行分类（如 AI 工具、生产力工具、开发者工具等）
   - 识别每个类别的主要特点和创新点

2. 市场趋势分析：
   - 总结当前产品发展的主要趋势
   - 分析这些趋势背后的技术和市场驱动因素
   - 预测可能的发展方向

3. 重点产品推荐：
   - 选择 3 个最值得关注的产品
   - 分析每个产品的：
     * 创新性和独特卖点
     * 解决的具体问题
     * 市场潜力
     * 推荐理由

原始内容如下：
{content}

请以结构化的方式呈现分析结果，确保内容清晰易读。"""
        
        # 调用 API 进行分析
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一位专业的科技产品分析师和趋势研究专家，擅长发现创新产品和分析市场趋势。请用专业、客观的视角分析内容。"
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,  # 适当提高创造性
                max_tokens=2000,  # 确保有足够的长度
            )
            
            summary = completion.choices[0].message.content
            
        except Exception as e:
            LOG.error(f"API 调用失败: {str(e)}")
            return f"内容分析失败: {str(e)}", None
        
        # 生成结构化报告
        report_content = f"""# 产品趋势分析报告

## 基本信息
- 生成时间：{current_date} {current_hour}:00
- 分析模型：{model_name}

## 分析报告
{summary}

## 原始数据
<details>
<summary>点击展开原始内容</summary>

{content}
</details>

---
*本报告由 AI 辅助生成，仅供参考*
"""
        
        # 保存报告
        try:
            report_dir = os.path.join('reports', current_date)
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f'trend_analysis_{current_hour}.md')
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            LOG.info(f"报告已保存: {report_path}")
            return report_content, report_path
            
        except Exception as e:
            LOG.error(f"保存报告失败: {str(e)}")
            return report_content, None
        
    except Exception as e:
        LOG.error(f"生成报告过程中发生未知错误: {str(e)}")
        return f"生成报告失败: {str(e)}", None

with gr.Blocks(title="我的信息收集工具") as iface:
    with gr.Tab("机器之心 - AI 资讯收集"):
        gr.Markdown("> 机器之心是一家成立于2015年，位于北京的人工智能信息服务平台。它提供包括媒体、数据信息产品、研究和活动在内的多种服务，旨在帮助用户进行人工智能相关决策。该平台覆盖了人工智能前沿技术研究、技术解读、算法实现和行业应用等方面，并且拥有成熟的中英文内容生产分发体系")
        model_type = gr.Radio(
            ["doubao"], 
            label="模型选择", 
            info="使用特定的模型进行总结", 
            value=DEFAULT_MODEL_TYPE
        )
        
        # 获取默认的模型选择器和模型ID
        model_name, default_model_id = get_default_model_name_list()
        
        # 添加一个文本组件来显示选择的模型ID，并设置默认值
        selected_model_id = gr.Textbox(
            label="选中的模型ID", 
            interactive=False,
            value=default_model_id  # 设置默认值
        )
        
        model_type.change(fn=update_model_name_list, inputs=model_type, outputs=model_name)
        model_name.change(fn=on_model_select, inputs=model_name, outputs=selected_model_id)

        # 新增一个按钮来触发新闻收集
        button = gr.Button("生成最新动态")

        # 设置输出组件
        markdown_output = gr.Markdown()
        file_output = gr.File(label="下载报告")

        # 将按钮点击事件与导出函数绑定
        button.click(generate_jixiezhixin_topic, inputs=[model_type, model_name,], outputs=[markdown_output, file_output])

# 启动接口
iface.launch(share=True, server_name="0.0.0.0")