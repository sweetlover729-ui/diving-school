"""
DOCX 文书自动解析器
自动识别表单字段，生成 fields_schema
"""
import json
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """表单字段定义"""
    id: str
    type: str  # text, radio, checkbox, signature, date
    label: str
    question: str = ""
    required: bool = True
    options: list[str] = None
    placeholder: str = ""
    # 自动填充配置
    auto_fill: str = ""  # student_name, student_phone, student_id_card, etc.
    editable: bool = True  # 是否允许学员修改


class DocumentParser:
    """DOCX 文档解析器"""

    # 命名空间
    NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    }

    # 自动填充字段映射
    AUTO_FILL_MAP = {
        '姓名': 'student_name',
        '名字': 'student_name',
        '学员姓名': 'student_name',
        '您的姓名': 'student_name',
        '拼音': 'student_name_pinyin',
        '手机': 'student_phone',
        '电话': 'student_phone',
        '个人电话': 'student_phone',
        '身份证号': 'student_id_card',
        '身份证': 'student_id_card',
        '出生年月': 'student_birth_date',
        '出生日期': 'student_birth_date',
        '年龄': 'student_age',
        '性别': 'student_gender',
        '单位名称': 'company_name',
        '工作地址': 'work_address',
        '职业': 'occupation',
        '职务': 'position',
        '教练': 'instructor_name',
        '培训中心': 'training_center',
        '课程地址': 'course_address',
        '紧急联络人': 'emergency_contact',
        '紧急联系人': 'emergency_contact',
    }

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.full_text = ""
        self.paragraphs = []

    def parse(self) -> list[FormField]:
        """解析 DOCX 文件，返回表单字段列表"""
        # 读取文档内容
        self._extract_text()

        fields = []
        field_id = 0

        # 1. 识别文本填空字段（冒号+空格模式）
        text_fields = self._detect_text_fields()
        for label, context in text_fields:
            field_id += 1
            auto_fill = self._get_auto_fill_mapping(label)
            fields.append(FormField(
                id=f"field_{field_id:03d}",
                type="text",
                label=label,
                question=context,
                required=True,
                auto_fill=auto_fill,
                editable=(auto_fill not in ['student_name', 'student_id_card'])  # 姓名和身份证不可修改
            ))

        # 2. 识别有/无单选
        yes_no_fields = self._detect_yes_no_fields()
        for label, context in yes_no_fields:
            field_id += 1
            fields.append(FormField(
                id=f"field_{field_id:03d}",
                type="radio",
                label=label,
                question=context,
                required=True,
                options=["有", "无"]
            ))

        # 3. 识别选项单选（A/B/C 或 初中/高中/大专）
        choice_fields = self._detect_choice_fields()
        for label, options, context in choice_fields:
            field_id += 1
            fields.append(FormField(
                id=f"field_{field_id:03d}",
                type="radio",
                label=label,
                question=context,
                required=True,
                options=options
            ))

        # 4. 识别签名字段
        signature_fields = self._detect_signature_fields()
        for label, context in signature_fields:
            field_id += 1
            fields.append(FormField(
                id=f"field_{field_id:03d}",
                type="signature",
                label=label,
                question=context,
                required=True
            ))

        # 5. 识别日期字段
        date_fields = self._detect_date_fields()
        for label, context in date_fields:
            field_id += 1
            auto_fill = "current_date" if "日期" in label or "今日" in label else ""
            fields.append(FormField(
                id=f"field_{field_id:03d}",
                type="date",
                label=label,
                question=context,
                required=True,
                auto_fill=auto_fill
            ))

        return fields

    def _extract_text(self):
        """提取文档文本，保留段落结构"""
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            xml_content = z.read('word/document.xml')

        root = ET.fromstring(xml_content)

        # 提取所有段落
        for paragraph in root.findall('.//w:p', self.NS):
            texts = []
            for elem in paragraph.iter():
                if elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t':
                    if elem.text:
                        texts.append(elem.text)
            para_text = ''.join(texts)
            if para_text.strip():
                self.paragraphs.append(para_text)

        self.full_text = '\n'.join(self.paragraphs)

    def _detect_text_fields(self) -> list[tuple]:
        """检测文本填空字段（冒号+空格模式）"""
        fields = []

        # 模式1: 字段名：    （冒号+3个以上空格）
        pattern1 = r'([^：:\n]{1,20})[：:]\s{3,}'
        matches = re.finditer(pattern1, self.full_text)
        for m in matches:
            label = m.group(1).strip()
            # 过滤掉非字段内容
            if len(label) >= 2 and not self._is_noise(label):
                # 获取上下文（前后50字符）
                start = max(0, m.start() - 50)
                end = min(len(self.full_text), m.end() + 50)
                context = self.full_text[start:end]
                fields.append((label, context))

        # 模式2: 横线填空 __________
        pattern2 = r'([^_\n]{2,20})[_]{3,}'
        matches = re.finditer(pattern2, self.full_text)
        for m in matches:
            label = m.group(1).strip()
            if len(label) >= 2 and not self._is_noise(label):
                start = max(0, m.start() - 30)
                end = min(len(self.full_text), m.end() + 30)
                context = self.full_text[start:end]
                fields.append((label, context))

        return fields

    def _detect_yes_no_fields(self) -> list[tuple]:
        """检测有/无单选字段"""
        fields = []
        pattern = r'([^。，,\n]{2,30})(?:有\s*[、,]\s*无|是\s*[、,]\s*否)'
        matches = re.finditer(pattern, self.full_text)
        for m in matches:
            label = m.group(1).strip()
            if len(label) >= 2:
                start = max(0, m.start() - 30)
                end = min(len(self.full_text), m.end() + 20)
                context = self.full_text[start:end]
                fields.append((label, context))
        return fields

    def _detect_choice_fields(self) -> list[tuple]:
        """检测选项单选字段（A/B/C 或 具体选项）"""
        fields = []

        # 模式: 数字开头的问题 + 选项
        # 如: "4、您的教育程度： 初中    中技/高中  大专    本科"
        pattern = r'(\d+[、.．]\s*[^：:\n]{2,20})[：:]\s*((?:[^\s]{2,10}\s+){2,}[^\s]{2,10})'
        matches = re.finditer(pattern, self.full_text)
        for m in matches:
            label = m.group(1).strip()
            options_text = m.group(2).strip()
            # 分割选项（2个以上空格分隔）
            options = [opt.strip() for opt in re.split(r'\s{2,}', options_text) if opt.strip()]
            if len(options) >= 2:
                start = max(0, m.start() - 20)
                end = min(len(self.full_text), m.end() + 20)
                context = self.full_text[start:end]
                fields.append((label, options, context))

        return fields

    def _detect_signature_fields(self) -> list[tuple]:
        """检测签名字段"""
        fields = []
        keywords = ['签名', '签字', '签署', '学员签名', '教练签名', '监护人签名', '亲属签名']

        for keyword in keywords:
            pattern = rf'({keyword}[:：]?\s*)'
            matches = re.finditer(pattern, self.full_text)
            for m in matches:
                label = m.group(1).strip()
                start = max(0, m.start() - 30)
                end = min(len(self.full_text), m.end() + 30)
                context = self.full_text[start:end]
                fields.append((label, context))

        return fields

    def _detect_date_fields(self) -> list[tuple]:
        """检测日期字段"""
        fields = []
        # 模式: 年    月    日
        # 查找日期标签
        date_labels = ['日期', '签署日期', '填写日期', '培训日期', '开始日期', '结束日期']
        for label in date_labels:
            if label in self.full_text:
                idx = self.full_text.find(label)
                start = max(0, idx - 20)
                end = min(len(self.full_text), idx + 40)
                context = self.full_text[start:end]
                fields.append((label, context))

        return fields

    def _is_noise(self, text: str) -> bool:
        """判断是否为噪声（非字段内容）"""
        noise_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^[一二三四五六七八九十\d]+[、.．]',
            r'^第[\d]+节',
            r'^\d+$',  # 纯数字
        ]
        for pattern in noise_patterns:
            if re.match(pattern, text):
                return True
        return False

    def _get_auto_fill_mapping(self, label: str) -> str:
        """获取自动填充映射"""
        for key, value in self.AUTO_FILL_MAP.items():
            if key in label:
                return value
        return ""

    def generate_schema(self) -> dict[str, Any]:
        """生成完整的 fields_schema"""
        fields = self.parse()
        return {
            "version": "1.0",
            "parser": "docx_auto_parser",
            "total_fields": len(fields),
            "fields": [asdict(f) for f in fields]
        }

    def save_schema(self, output_path: str):
        """保存 schema 到 JSON 文件"""
        schema = self.generate_schema()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        return schema


# 测试代码
if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) > 1:
        docx_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else "schema.json"

        parser = DocumentParser(docx_path)
        schema = parser.save_schema(output_path)

        logger.info("解析完成！")
        logger.info(f"总字段数: {schema['total_fields']}")
        logger.info("\n字段列表:")
        for field in schema['fields']:
            logger.info(f"  [{field['type']}] {field['label']}")
            if field.get('auto_fill'):
                logger.info(f"      -> 自动填充: {field['auto_fill']}")
    else:
        # 测试4份文书
        docs = [
            ('/Users/wjjmac/book/中国潜水同意书.docx', 'consent_form'),
            ('/Users/wjjmac/book/潜水员健康声明书暨健康调查文书.docx', 'health_decl'),
            ('/Users/wjjmac/book/一般免责和风险承担协议书.docx', 'liability_waiver'),
            ('/Users/wjjmac/book/潜水（应急救援）培训学员问卷调查.docx', 'questionnaire'),
        ]

        for docx_path, name in docs:
            if os.path.exists(docx_path):
                logger.info(f"\n{'='*60}")
                logger.info(f"解析: {name}")
                logger.info('='*60)
                parser = DocumentParser(docx_path)
                schema = parser.generate_schema()
                logger.info(f"总字段数: {schema['total_fields']}")
                for field in schema['fields'][:10]:  # 只显示前10个
                    auto = f" (auto:{field['auto_fill']})" if field.get('auto_fill') else ""
                    logger.info(f"  [{field['type']}] {field['label']}{auto}")
                if len(schema['fields']) > 10:
                    logger.info(f"  ... 还有 {len(schema['fields'])-10} 个字段")
