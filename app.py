from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from openai import OpenAI
import os

app = Flask(__name__)
CORS(app)

# ========== 请在这里填写你的DeepSeek API密钥 ==========
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
# =====================================================

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI编程学习助手</title>
    <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs/loader.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1e1e1e; color: #d4d4d4; display: flex; height: 100vh; }
        .left-panel { width: 50%; display: flex; flex-direction: column; }
        .editor-area { flex: 1; border-bottom: 2px solid #333; }
        .submit-btn {
            background: #007acc; color: white; border: none; padding: 12px 30px;
            font-size: 16px; cursor: pointer; margin: 10px; border-radius: 4px;
        }
        .submit-btn:hover { background: #005a9e; }
        .language-select { margin: 10px; padding: 8px 12px; background: #333; color: white; border: 1px solid #555; border-radius: 4px; }
        .right-panel { width: 50%; overflow-y: auto; padding: 20px; border-left: 2px solid #333; }
        .result-section { margin-bottom: 20px; }
        .result-section h3 { color: #007acc; margin-bottom: 10px; border-bottom: 1px solid #444; padding-bottom: 5px; }
        .correct { color: #4ec9b0; font-weight: bold; }
        .wrong { color: #f44747; font-weight: bold; }
        .error-loc { background: #2d2d2d; padding: 10px; border-left: 3px solid #f44747; margin: 5px 0; }
        .suggestion { background: #2d2d2d; padding: 10px; border-left: 3px solid #4ec9b0; margin: 5px 0; }
        .exercise-box { background: #2d2d2d; padding: 15px; border-left: 3px solid #007acc; margin: 10px 0; }
        pre { background: #1e1e1e; padding: 10px; border-radius: 4px; overflow-x: auto; }
        code { font-family: 'Courier New', monospace; }
        .loading { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <div class="left-panel">
        <div style="display: flex; align-items: center; gap: 10px;">
            <select class="language-select" id="languageSelect" onchange="changeLanguage()">
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
            </select>
        </div>
        <div id="editorContainer" class="editor-area"></div>
        <button class="submit-btn" onclick="submitCode()">🔍 提交代码分析</button>
    </div>
    <div class="right-panel" id="resultPanel">
        <div style="color: #888; text-align: center; padding: 100px 0;">
            <h2>👋 欢迎使用AI编程学习助手</h2>
            <p style="margin-top: 20px;">在左侧编写代码，然后点击“提交代码分析”</p >
            <p>AI将帮你判断代码是否正确、定位逻辑错误、给出修改意见</p >
            <p>并为你生成变式练习题</p >
        </div>
    </div>

    <script>
        require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' } });
        let editor;
        require(['vs/editor/editor.main'], function () {
            editor = monaco.editor.create(document.getElementById('editorContainer'), {
                value: '# 在这里编写你的代码\\ndef factorial(n):\\n    if n == 0:\\n        return 1\\n    else:\\n        return n * factorial(n - 1)\\n\\nprint(factorial(5))',
                language: 'python',
                theme: 'vs-dark',
                fontSize: 14,
                automaticLayout: true,
                minimap: { enabled: false }
            });
        });

        function changeLanguage() {
            const lang = document.getElementById('languageSelect').value;
            const langMap = { 'python': 'python', 'javascript': 'javascript', 'java': 'java', 'cpp': 'cpp' };
            monaco.editor.setModelLanguage(editor.getModel(), langMap[lang] || 'python');
        }

        async function submitCode() {
            const code = editor.getValue();
            const language = document.getElementById('languageSelect').value;
            const resultPanel = document.getElementById('resultPanel');
            resultPanel.innerHTML = '<div class="loading"><h3>🤖 AI正在分析你的代码...</h3><p>请稍候，正在调用DeepSeek进行深度分析</p ></div>';

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code, language: language })
                });
                const data = await response.json();
                if (data.error) { resultPanel.innerHTML = '<p style="color:red;">错误：' + data.error + '</p >'; return; }
                resultPanel.innerHTML = data.html;
            } catch (e) {
                resultPanel.innerHTML = '<p style="color:red;">请求失败：' + e.message + '</p >';
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    user_code = data.get('code', '')
    language = data.get('language', 'python')

    prompt = f'''你是一位专业的编程教师。请分析以下{language}代码，严格按照下面的格式输出：

## 一、判断结果
【正确 ✓ / 错误 ✗】+ 一句话总结

## 二、逻辑错误定位（如果有错误）
逐条列出代码中的逻辑错误，标明具体位置和错误类型。

## 三、错误原因解释
用通俗易懂的语言解释每个错误的原因，适合编程学习者理解。

## 四、修改建议
给出具体的修改方案和修正后的代码。

## 五、变式练习
生成一道与本题同类型、同难度的变式练习题，包含题目描述。

---
用户代码（{language}）：
```{language}
{user_code}
```'''

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "你是一位耐心、专业的编程教师，擅长用通俗语言解释代码问题。请严格按要求的格式输出。"},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096
        )
        analysis = response.choices[0].message.content

        html = convert_to_html(analysis, user_code, language)
        return jsonify({"html": html})
    except Exception as e:
        return jsonify({"error": str(e)})

def convert_to_html(analysis, user_code, language):
    analysis = analysis.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    analysis = analysis.replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')

    has_error = '错误' in analysis[:200] or '✗' in analysis[:200]

    html = f'''
    <div class="result-section">
        <h3>📋 你提交的代码</h3>
        <pre><code class="language-{language}">{user_code}</code></pre>
    </div>
    <div class="result-section">
        <h3>🔍 分析结果</h3>
        <div class="{'correct' if not has_error else 'wrong'}">'''

    lines = analysis.split('\n')
    current_section = None
    for line in lines:
        line_stripped = line.strip()
        if '## 一、判断结果' in line_stripped or '一、判断结果' in line_stripped:
            current_section = 'judge'
            html += f'<h4 style="margin-top:15px; color:#569cd6;">📊 {line_stripped}</h4>'
        elif '## 二、逻辑错误' in line_stripped or '二、逻辑错误' in line_stripped:
            current_section = 'error'
            html += f'<h4 style="margin-top:15px; color:#569cd6;">🐛 {line_stripped}</h4>'
        elif '## 三、错误原因' in line_stripped or '三、错误原因' in line_stripped:
            current_section = 'reason'
            html += f'<h4 style="margin-top:15px; color:#569cd6;">💡 {line_stripped}</h4>'
        elif '## 四、修改建议' in line_stripped or '四、修改建议' in line_stripped:
            current_section = 'suggestion'
            html += f'<h4 style="margin-top:15px; color:#569cd6;">🔧 {line_stripped}</h4>'
        elif '## 五、变式练习' in line_stripped or '五、变式练习' in line_stripped:
            current_section = 'exercise'
            html += f'<h4 style="margin-top:15px; color:#569cd6;">🏋️ {line_stripped}</h4>'
        elif '```' in line_stripped:
            if current_section == 'suggestion' or current_section == 'exercise':
                html += '<pre><code>'
            else:
                html += '<pre><code>'
        elif line_stripped:
            html += f'<p>{line_stripped}</p >'

    html += '</div></div>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
