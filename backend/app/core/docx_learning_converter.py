"""
DOCX 转互动式学习 JSON 转换器
将 Word 教材转换为结构化学习数据
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class LearningUnit:
    """学习单元（段落/知识点）"""
    id: str
    type: str  # paragraph, heading, key_concept, quiz_placeholder
    content: str
    level: int = 0  # 标题级别
    keywords: List[str] = None
    quiz: Dict = None  # 嵌入式测验


@dataclass
class LearningSection:
    """学习章节"""
    id: str
    title: str
    level: int
    units: List[LearningUnit]
    estimated_time: int = 10  # 预计阅读时间（分钟）
    key_concepts: List[str] = None


@dataclass
class InteractiveTextbook:
    """互动式教材"""
    id: str
    title: str
    total_sections: int
    sections: List[LearningSection]
    key_concepts_map: Dict[str, str]  # 知识点解释映射


class DocxToLearningConverter:
    """DOCX 转互动学习格式转换器"""
    
    NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    }
    
    # 知识点自动识别关键词（潜水专业）
    KEY_CONCEPT_PATTERNS = [
        r'氮醉', r'减压病', r'耳压平衡', r'浮力控制', r'安全停留',
        r'减压停留', r'上升速度', r'潜水计划', r'气体管理', r'潜伴制度',
        r'紧急上升', r'备用气源', r'深度限制', r'免减压极限', r'重复潜水',
        r'水面间隔', r'残余氮气', r'高氧空气', r'空气消耗率', r'中性浮力',
        r'正浮力', r'负浮力', r'配重', r'BCD', r'调节器',
        r'气瓶', r'压力表', r'深度表', r'指北针', r'潜水电脑',
    ]
    
    # 可生成测验的句式模式
    QUIZ_PATTERNS = [
        (r'(.{10,50})是(.{5,30})的', 'concept_definition'),
        (r'(.{5,30})包括(.{10,60})', 'enumeration'),
        (r'(.{10,50})应该(.{5,40})', 'procedure'),
        (r'(.{5,30})不能(.{5,30})', 'prohibition'),
        (r'(.{10,50})必须(.{5,40})', 'requirement'),
    ]
    
    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.full_text = ""
        self.paragraphs = []
        self.title = ""
        
    def convert(self) -> InteractiveTextbook:
        """转换 DOCX 为互动学习格式"""
        # 提取文本和结构
        self._extract_structure()
        
        # 解析章节结构
        sections = self._parse_sections()
        
        # 提取知识点
        key_concepts_map = self._extract_key_concepts()
        
        # 为每个章节生成测验点
        for section in sections:
            self._generate_quizzes(section)
            section.key_concepts = self._find_section_concepts(section)
        
        # 生成教材ID
        book_id = hashlib.md5(self.title.encode()).hexdigest()[:8]
        
        return InteractiveTextbook(
            id=book_id,
            title=self.title,
            total_sections=len(sections),
            sections=sections,
            key_concepts_map=key_concepts_map
        )
    
    def _extract_structure(self):
        """提取文档结构和文本"""
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            xml_content = z.read('word/document.xml')
        
        root = ET.fromstring(xml_content)
        
        for paragraph in root.findall('.//w:p', self.NS):
            # 获取段落文本
            texts = []
            for elem in paragraph.iter():
                if elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t':
                    if elem.text:
                        texts.append(elem.text)
            
            para_text = ''.join(texts).strip()
            if not para_text:
                continue
            
            # 检测标题级别
            level = 0
            pStyle = paragraph.find('.//w:pStyle', self.NS)
            if pStyle is not None:
                style_val = pStyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '')
                if 'Heading' in style_val:
                    try:
                        level = int(style_val.replace('Heading', ''))
                    except (ValueError, TypeError):
                        pass
                elif style_val.startswith('标题'):
                    try:
                        level = int(style_val.replace('标题', ''))
                    except (ValueError, TypeError):
                        pass
            
            # 根据字体大小判断标题
            if level == 0:
                sz = paragraph.find('.//w:sz', self.NS)
                if sz is not None:
                    sz_val = sz.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '0')
                    try:
                        if int(sz_val) >= 36:  # 18pt
                            level = 1
                        elif int(sz_val) >= 28:  # 14pt
                            level = 2
                    except (ValueError, TypeError):
                        pass
            
            self.paragraphs.append({
                'text': para_text,
                'level': level,
                'is_heading': level > 0
            })
            
            # 第一个一级标题作为书名
            if level == 1 and not self.title:
                self.title = para_text
        
        # 如果没有检测到标题，使用文件名
        if not self.title:
            self.title = self.docx_path.split('/')[-1].replace('.docx', '')
        
        self.full_text = '\n'.join([p['text'] for p in self.paragraphs])
    
    def _parse_sections(self) -> List[LearningSection]:
        """解析章节结构"""
        sections = []
        current_section = None
        current_units = []
        section_counter = 0
        
        for para in self.paragraphs:
            # 新章节开始
            if para['is_heading'] and para['level'] <= 2:
                # 保存上一个章节
                if current_section and current_units:
                    current_section.units = current_units
                    current_section.estimated_time = self._calculate_reading_time(current_units)
                    sections.append(current_section)
                
                # 创建新章节
                section_counter += 1
                current_section = LearningSection(
                    id=f"sec_{section_counter:03d}",
                    title=para['text'],
                    level=para['level'],
                    units=[],
                    estimated_time=10,
                    key_concepts=[]
                )
                current_units = []
                
                # 添加标题作为单元
                current_units.append(LearningUnit(
                    id=f"u_{section_counter}_h",
                    type='heading',
                    content=para['text'],
                    level=para['level']
                ))
            else:
                # 普通段落
                if current_section is None:
                    # 第一个段落之前没有标题，创建默认章节
                    section_counter += 1
                    current_section = LearningSection(
                        id=f"sec_{section_counter:03d}",
                        title="前言",
                        level=1,
                        units=[],
                        estimated_time=10,
                        key_concepts=[]
                    )
                    current_units = []
                
                unit_id = f"u_{section_counter}_{len(current_units)}"
                
                # 检测是否是知识点段落
                is_concept, keywords = self._detect_key_concept(para['text'])
                
                unit = LearningUnit(
                    id=unit_id,
                    type='key_concept' if is_concept else 'paragraph',
                    content=para['text'],
                    level=0,
                    keywords=keywords
                )
                current_units.append(unit)
        
        # 保存最后一个章节
        if current_section and current_units:
            current_section.units = current_units
            current_section.estimated_time = self._calculate_reading_time(current_units)
            sections.append(current_section)
        
        return sections
    
    def _detect_key_concept(self, text: str) -> tuple:
        """检测段落是否包含关键概念"""
        keywords = []
        for pattern in self.KEY_CONCEPT_PATTERNS:
            if re.search(pattern, text):
                keywords.append(pattern)
        return len(keywords) > 0, keywords
    
    def _extract_key_concepts(self) -> Dict[str, str]:
        """提取所有知识点及其解释"""
        concepts = {}
        
        for pattern in self.KEY_CONCEPT_PATTERNS:
            # 查找包含该知识点的段落
            for para in self.paragraphs:
                if re.search(pattern, para['text']):
                    # 提取定义（通常是"XXX是YYY"或"XXX指YYY"）
                    text = para['text']
                    
                    # 尝试提取定义
                    definition = self._extract_definition(text, pattern)
                    if definition:
                        concepts[pattern] = definition
                    else:
                        # 使用段落前100字作为解释
                        concepts[pattern] = text[:100] + '...' if len(text) > 100 else text
                    break
        
        return concepts
    
    def _extract_definition(self, text: str, concept: str) -> Optional[str]:
        """从文本中提取概念定义"""
        # 模式1: XXX是YYY
        match = re.search(rf'{concept}[是|指|为]([^。，]+)', text)
        if match:
            return match.group(1).strip()
        
        # 模式2: YYY的XXX
        match = re.search(rf'([^。，]+)的{concept}', text)
        if match:
            return match.group(1).strip() + concept
        
        return None
    
    def _find_section_concepts(self, section: LearningSection) -> List[str]:
        """找出章节包含的所有知识点"""
        concepts = set()
        for unit in section.units:
            if unit.keywords:
                concepts.update(unit.keywords)
        return list(concepts)
    
    def _generate_quizzes(self, section: LearningSection):
        """为章节生成嵌入式测验"""
        quiz_counter = 0
        
        for i, unit in enumerate(section.units):
            if unit.type != 'paragraph':
                continue
            
            text = unit.content
            
            # 尝试匹配测验模式
            for pattern, quiz_type in self.QUIZ_PATTERNS:
                match = re.search(pattern, text)
                if match and len(text) < 200:  # 短段落更适合做测验
                    quiz_counter += 1
                    
                    # 生成测验
                    if quiz_type == 'concept_definition':
                        quiz = self._create_definition_quiz(match, text)
                    elif quiz_type == 'enumeration':
                        quiz = self._create_enumeration_quiz(match, text)
                    elif quiz_type == 'procedure':
                        quiz = self._create_procedure_quiz(match, text)
                    elif quiz_type == 'prohibition':
                        quiz = self._create_prohibition_quiz(match, text)
                    elif quiz_type == 'requirement':
                        quiz = self._create_requirement_quiz(match, text)
                    else:
                        continue
                    
                    if quiz:
                        unit.quiz = quiz
                        unit.type = 'quiz_placeholder'
                    break
    
    def _create_definition_quiz(self, match, text) -> Dict:
        """创建定义类测验"""
        subject = match.group(1)
        definition = match.group(2)
        
        return {
            'id': f'quiz_{hashlib.md5(text.encode()).hexdigest()[:8]}',
            'type': 'single_choice',
            'question': f'{subject}是指什么？',
            'options': [
                definition,
                '一种潜水装备',
                '潜水认证等级',
                '潜水俱乐部名称'
            ],
            'correct': 0,
            'explanation': f'根据教材内容：{text[:100]}'
        }
    
    def _create_enumeration_quiz(self, match, text) -> Dict:
        """创建列举类测验"""
        subject = match.group(1)
        items = match.group(2)
        
        # 提取列举项
        item_list = re.split(r'[、，,；;]', items)
        item_list = [i.strip() for i in item_list if len(i.strip()) > 1]
        
        if len(item_list) < 2:
            return None
        
        return {
            'id': f'quiz_{hashlib.md5(text.encode()).hexdigest()[:8]}',
            'type': 'multiple_choice',
            'question': f'{subject}包括以下哪些？（多选）',
            'options': item_list[:4] if len(item_list) >= 4 else item_list + ['其他选项'],
            'correct': list(range(len(item_list))) if len(item_list) <= 4 else [0, 1],
            'explanation': f'教材中提到：{items}'
        }
    
    def _create_procedure_quiz(self, match, text) -> Dict:
        """创建程序类测验"""
        subject = match.group(1)
        action = match.group(2)
        
        return {
            'id': f'quiz_{hashlib.md5(text.encode()).hexdigest()[:8]}',
            'type': 'single_choice',
            'question': f'{subject}时应该怎么做？',
            'options': [
                action,
                '快速上升',
                '继续下潜',
                '忽略不管'
            ],
            'correct': 0,
            'explanation': f'正确做法：{action}'
        }
    
    def _create_prohibition_quiz(self, match, text) -> Dict:
        """创建禁止类测验"""
        subject = match.group(1)
        action = match.group(2)
        
        return {
            'id': f'quiz_{hashlib.md5(text.encode()).hexdigest()[:8]}',
            'type': 'single_choice',
            'question': f'潜水时{subject}可以{action}吗？',
            'options': [
                '不可以，这是危险的',
                '可以，没有问题',
                '视情况而定',
                '只有教练可以'
            ],
            'correct': 0,
            'explanation': f'教材明确指出：{subject}不能{action}'
        }
    
    def _create_requirement_quiz(self, match, text) -> Dict:
        """创建要求类测验"""
        subject = match.group(1)
        requirement = match.group(2)
        
        return {
            'id': f'quiz_{hashlib.md5(text.encode()).hexdigest()[:8]}',
            'type': 'single_choice',
            'question': f'{subject}时必须注意什么？',
            'options': [
                requirement,
                '尽快完成',
                '节省空气',
                '追逐海洋生物'
            ],
            'correct': 0,
            'explanation': f'教材要求：{subject}必须{requirement}'
        }
    
    def _calculate_reading_time(self, units: List[LearningUnit]) -> int:
        """计算预计阅读时间（分钟）"""
        total_chars = sum(len(u.content) for u in units)
        # 按每分钟300字计算
        minutes = max(3, total_chars // 300)
        return min(minutes, 30)  # 最多30分钟
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        textbook = self.convert()
        return json.dumps(asdict(textbook), ensure_ascii=False, indent=2)
    
    def save_json(self, output_path: str):
        """保存为 JSON 文件"""
        json_str = self.to_json()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        return json_str


# 测试
if __name__ == "__main__":
    import sys
    import os
    
    # 测试4份教材
    docs = [
        ('/Users/wjjmac/book/应急救援潜水五级课程教材(V11.12).docx', 'main_textbook'),
    ]
    
    for docx_path, name in docs:
        if os.path.exists(docx_path):
            logger.info(f"\n{'='*60}")
            logger.info(f"转换: {name}")
            logger.info('='*60)
            
            converter = DocxToLearningConverter(docx_path)
            textbook = converter.convert()
            
            logger.info(f"教材标题: {textbook.title}")
            logger.info(f"章节数: {textbook.total_sections}")
            logger.info(f"知识点数: {len(textbook.key_concepts_map)}")
            
            # 显示前3个章节
            for sec in textbook.sections[:3]:
                quiz_count = sum(1 for u in sec.units if u.quiz)
                logger.info(f"\n  [{sec.id}] {sec.title}")
                logger.info(f"    单元数: {len(sec.units)}, 预计时间: {sec.estimated_time}分钟")
                logger.info(f"    测验数: {quiz_count}")
                logger.info(f"    知识点: {', '.join(sec.key_concepts[:3])}")
            
            # 保存JSON
            output_path = f"/tmp/{name}_learning.json"
            converter.save_json(output_path)
            logger.info(f"\n已保存到: {output_path}")
