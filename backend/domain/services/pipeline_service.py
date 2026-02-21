from pathlib import Path
from typing import Callable, Dict, List, Optional


def script_args(
    step: str,
    search: Optional[str],
    query: Optional[str],
    script_path_resolver: Callable[[str], Path],
) -> List[str]:
    script = script_path_resolver(step)
    args = [str(script)]
    if step == "scout" and search:
        args.extend(["--search", search])
    if step == "scout" and query:
        args.extend(["--query", query])
    return args


def script_args_with_size(
    step: str,
    search: str,
    size: str,
    query: str,
    size_presets: Dict[str, Dict[str, int]],
    script_path_resolver: Callable[[str], Path],
    eval_model: Optional[str] = None,
) -> List[str]:
    cfg = size_presets[size]
    args = script_args(step, search, query, script_path_resolver)
    if step == "scout":
        args.extend(["--max-results", str(cfg["max_results"])])
    if step == "shortlist":
        args.extend(["--target-n", str(cfg["shortlist_k"])])
    if step == "scrape":
        args.extend(["--limit", str(cfg["final_top"])])
    if step == "eval":
        args.extend(["--limit", str(cfg["final_top"])])
        if eval_model:
            args.extend(["--model", eval_model])
    if step == "sort":
        args.extend(["--final-top", str(cfg["final_top"])])
    return args
