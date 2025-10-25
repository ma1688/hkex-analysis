"""合成分析工具 - 基于LLM的内容合成和信息提取"""
import json
import logging

from langchain_core.tools import tool

from src.llm.manager import get_llm_manager
from src.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


@tool
def synthesize_chunks(chunks_json: str) -> str:
    """将多个chunks合成连贯文本
    
    【适用场景】
    - retrieve_chunks返回了多个内容块，需要整合为连贯文本
    - 公告内容被分散在多个页面，需要汇总
    - 作为extract_key_info的前置步骤
    
    【不适用场景】
    - 只有1-2个chunk且内容简短 → 直接使用即可
    - 需要结构化提取 → 直接用 extract_key_info
    
    【前置条件】
    - 必须提供JSON格式的chunks数组（从retrieve_chunks获取）
    - chunks需要包含text字段
    
    【返回格式】
    整合后的连贯文本（字符串）
    
    【后续工具链】
    - 提取结构化信息 → extract_key_info(text=synthesized_text)
    - 对比分析 → 如有多个文档，分别synthesize后用 compare_data
    
    【使用示例】
    chunks = retrieve_chunks(doc_id="xxx", limit=30)
    synthesized = synthesize_chunks(chunks_json=chunks)
    
    Args:
        chunks_json: JSON格式的chunks列表（通常来自retrieve_chunks的结果）
        
    Returns:
        合成后的连贯文本
    """
    try:
        # 解析chunks
        chunks_data = json.loads(chunks_json)

        if not chunks_data:
            return "没有可合成的内容"

        # 提取文本并按chunk_index排序
        if isinstance(chunks_data, list):
            chunks = sorted(chunks_data, key=lambda x: x.get("chunk_index", 0))
            texts = [chunk.get("text", "") for chunk in chunks]
        else:
            return "输入格式错误，需要JSON数组"

        # 合并文本
        combined_text = "\n\n".join(texts)

        # 使用LLM优化合成
        llm_manager = get_llm_manager()
        llm = llm_manager.get_model_for_task("summarize")

        prompt = f"""请将以下公告片段整合成连贯的文本，保留关键信息，去除重复内容：

{combined_text}

整合后的文本："""

        result = llm.invoke(prompt)
        synthesized = result.content if hasattr(result, 'content') else str(result)

        logger.info(f"合成chunks: {len(chunks)}个片段 → {len(synthesized)}字符")
        # 清理可能的无效字符
        return clean_text(synthesized)

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return f"JSON解析失败: {e}"
    except Exception as e:
        logger.error(f"合成chunks失败: {e}")
        return f"合成失败: {e}"


@tool
def extract_key_info(text: str, info_type: str = "summary") -> str:
    """从文本中提取关键信息
    
    【适用场景】
    - 从长文本中提取特定类型的结构化信息
    - 需要摘要、日期、金额、相关方等特定维度的信息
    - 作为synthesize_chunks的后续步骤
    
    【不适用场景】
    - 需要完整原文 → 使用 retrieve_chunks
    - 需要结构化数据 → 优先用 query_*_data 工具
    
    【前置条件】
    - 提供文本内容（可以是synthesize_chunks的输出或原始文本）
    - 指定info_type
    
    【info_type选项】
    - summary: 提取核心摘要和要点
    - financial_data: 提取金额、比率等财务数据
    - dates: 提取重要日期（公告日、生效日、截止日等）
    - parties: 提取相关方（公司、承销商、保荐人等）
    - terms: 提取关键条款
    
    【返回格式】
    JSON格式的结构化信息，具体字段取决于info_type
    
    【后续工具链】
    - 对比分析 → compare_data（对比不同文档的提取结果）
    
    【使用示例】
    # 提取摘要
    extract_key_info(text=synthesized_text, info_type="summary")
    
    # 提取财务数据
    extract_key_info(text=synthesized_text, info_type="financial_data")
    
    # 提取日期
    extract_key_info(text=synthesized_text, info_type="dates")
    
    Args:
        text: 输入文本（通常是合成后的chunks或原始文本）
        info_type: 信息类型，可选：summary/financial_data/dates/parties/terms
        
    Returns:
        结构化的关键信息（JSON格式）
    """
    try:
        llm_manager = get_llm_manager()
        llm = llm_manager.get_model_for_task("analyze")

        # 根据info_type选择不同的提取策略
        prompts = {
            "summary": f"""请从以下公告内容中提取核心摘要：

{text}

以JSON格式返回：
{{"summary": "核心摘要", "key_points": ["要点1", "要点2", ...]}}""",

            "financial_data": f"""请从以下内容中提取所有财务数据：

{text}

以JSON格式返回：
{{"amounts": [{{"type": "类型", "value": "金额", "currency": "币种"}}],
 "ratios": [{{"type": "类型", "value": "比率"}}]}}""",

            "dates": f"""请从以下内容中提取所有重要日期：

{text}

以JSON格式返回：
{{"dates": [{{"event": "事件", "date": "YYYY-MM-DD"}}]}}""",

            "parties": f"""请从以下内容中提取相关方信息：

{text}

以JSON格式返回：
{{"parties": [{{"role": "角色", "name": "名称"}}]}}""",

            "terms": f"""请从以下内容中提取关键条款：

{text}

以JSON格式返回：
{{"terms": [{{"term": "条款名", "value": "内容"}}]}}"""
        }

        prompt = prompts.get(info_type, prompts["summary"])
        result = llm.invoke(prompt)
        extracted = result.content if hasattr(result, 'content') else str(result)

        # 清理可能的无效字符
        extracted = clean_text(extracted)

        # 尝试解析为JSON验证格式
        try:
            json.loads(extracted)
        except:
            # 如果不是有效JSON，包装一下
            extracted = json.dumps({"result": extracted}, ensure_ascii=False)

        logger.info(f"提取关键信息: type={info_type}, 文本长度={len(text)}")
        return extracted

    except Exception as e:
        logger.error(f"提取关键信息失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def compare_data(data1_json: str, data2_json: str, comparison_dimensions: str = None) -> str:
    """对比两组数据
    
    【适用场景】
    - 对比两家公司的配售/供股条款
    - 对比同一公司不同时期的数据
    - 分析哪个方案更优
    
    【前置条件】
    - 两组数据必须是JSON格式
    - 建议提供comparison_dimensions明确对比维度
    
    【对比维度示例】
    - 配售：配售价、折让率、配售比例、承销商
    - IPO：发行价、募资额、市值、费用率
    - 供股：供股价、供股比例、包销商
    
    【返回】结构化的对比分析，包含主要差异、各自优势、综合评价
    
    Args:
        data1_json: 第一组数据（JSON格式）
        data2_json: 第二组数据（JSON格式）
        comparison_dimensions: 对比维度（可选，如"配售价,折让率,配售比例"）
        
    Returns:
        对比分析结果（自然语言描述）
    """
    try:
        llm_manager = get_llm_manager()
        llm = llm_manager.get_model_for_task("analyze")

        prompt = f"""请对比以下两组数据：

数据1：
{data1_json}

数据2：
{data2_json}

对比维度：{comparison_dimensions or '所有关键维度'}

请从以下角度分析：
1. 主要差异
2. 各自优势
3. 综合评价

以结构化方式返回对比结果。"""

        result = llm.invoke(prompt)
        comparison = result.content if hasattr(result, 'content') else str(result)

        logger.info(f"数据对比完成: dimensions={comparison_dimensions}")
        # 清理可能的无效字符
        return clean_text(comparison)

    except Exception as e:
        logger.error(f"数据对比失败: {e}")
        return f"对比失败: {e}"
