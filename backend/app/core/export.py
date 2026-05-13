"""
学员档案导出
"""
from datetime import datetime
from typing import Optional
import json


def generate_student_report(student_data: dict, progress_data: dict, exam_records: list) -> dict:
    """生成学员学习报告"""
    
    # 基本信息
    report = {
        "title": "消防潜水培训学习报告",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "student": {
            "name": student_data.get("real_name", ""),
            "phone": student_data.get("phone", ""),
            "level": student_data.get("current_level", 1),
        },
        "summary": {
            "total_lessons": progress_data.get("total_lessons", 0),
            "completed_lessons": progress_data.get("completed_lessons", 0),
            "progress_percent": progress_data.get("overall_progress", 0),
            "total_exams": len(exam_records),
            "passed_exams": len([e for e in exam_records if e.get("status") == "passed"]),
        },
        "exam_records": exam_records,
        "progress": progress_data,
    }
    
    return report


def export_to_json(data: dict) -> str:
    """导出为 JSON"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_to_text(data: dict) -> str:
    """导出为文本格式"""
    lines = [
        "=" * 50,
        data.get("title", "学习报告"),
        "=" * 50,
        f"生成时间: {data.get('generated_at', '')}",
        "",
        "学员信息:",
        f"  姓名: {data['student'].get('name', '')}",
        f"  手机: {data['student'].get('phone', '')}",
        f"  等级: {data['student'].get('level', 1)}星",
        "",
        "学习概况:",
        f"  总课时: {data['summary'].get('total_lessons', 0)}",
        f"  完成课时: {data['summary'].get('completed_lessons', 0)}",
        f"  学习进度: {data['summary'].get('progress_percent', 0)}%",
        f"  考试次数: {data['summary'].get('total_exams', 0)}",
        f"  通过次数: {data['summary'].get('passed_exams', 0)}",
        "",
    ]
    
    if data.get("exam_records"):
        lines.append("考试记录:")
        for i, exam in enumerate(data["exam_records"], 1):
            lines.append(f"  {i}. {exam.get('exam_title', '')} - {exam.get('score', 0)}分")
        lines.append("")
    
    lines.append("=" * 50)
    
    return "\n".join(lines)
