"""Command Line Interface for BitSignal (unified cycle model, Phase 1)."""

import argparse
import io
import os
import subprocess
import sys

from dotenv import load_dotenv

from bitsignal.backtest.engine import run_backtest

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load_cfg(args):
    """Config from ``--config`` (default: config/config.yaml, the dashboard model)."""
    from bitsignal.config import load_config

    return load_config(getattr(args, "config", None))


def cmd_backtest(args):
    """S5: backtest of the default model against the two Q1 benchmarks, offline (frozen CSV).

    Default window: calibration (no 2019+ criteria). ``--window development`` needs the frozen
    parameters file with a matching model_hash (S6).
    """
    from bitsignal.backtest.report import to_text
    from bitsignal.config import load_frozen_params
    from bitsignal.data.history import load_frozen_history

    cfg = _load_cfg(args)
    frozen = load_frozen_params(cfg.backtest.frozen_params)
    record = getattr(args, "record", False)
    if getattr(args, "variants", False):
        _backtest_variants(args, cfg, frozen, record)
        return
    if record:
        refusal = _record_refusal(args, cfg, frozen)
        if refusal:
            print(f"[RECUSADO] {refusal}")
            sys.exit(1)
    history = load_frozen_history(cfg.data.csv_path)
    try:
        report = run_backtest(
            history, cfg, window=args.window, frozen=frozen, sensitivities=not args.no_sensitivities
        )
    except ValueError as exc:
        print(f"[ERRO] {exc}")
        sys.exit(1)
    print(to_text(report))
    if record:
        _write_approval(cfg, frozen, report)
        return
    if args.window == "development" and frozen is not None and frozen.approval is not None:
        a = frozen.approval
        print("")
        print(f"Approval gravado no S6 ({a.run_at:%Y-%m-%d}): {a.passed.model_dump()} {a.values.model_dump()}")
        print("O recálculo acima é só exibição; o resultado oficial é o gravado.")


def _backtest_variants(args, cfg, frozen, record) -> None:
    """Phase 2: default model plus the comparison catalog (never recorded, never frozen)."""
    from bitsignal.backtest.engine import run_variants
    from bitsignal.backtest.report import variants_to_text
    from bitsignal.data.history import load_frozen_history

    if record:
        print("[RECUSADO] --record não vale com --variants: variantes nunca são gravadas.")
        sys.exit(1)
    try:
        res = run_variants(load_frozen_history(cfg.data.csv_path), cfg, window=args.window, frozen=frozen)
    except ValueError as exc:
        print(f"[ERRO] {exc}")
        sys.exit(1)
    print(variants_to_text(res, args.window))


# --------------------------------------------------------------------------------------
# S6 — freeze and single 2019+ evaluation (design plan item 35)
# --------------------------------------------------------------------------------------

TECHNICAL_TESTS = [
    "tests/test_weekly.py",
    "tests/test_score.py",
    "tests/test_detector.py",
    "tests/test_detector_golden.py",
    "tests/test_cycle.py",
    "tests/test_no_lookahead.py",
    "tests/test_parity.py",
    "tests/test_backtest.py",
    "tests/test_golden.py",
]


def _run_technical_tests() -> bool:
    """Run the single list of technical tests (Verification Plan) without coverage."""
    from bitsignal.config import REPO_ROOT

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-cov", *TECHNICAL_TESTS], cwd=str(REPO_ROOT)
    )
    return proc.returncode == 0


def _git_committed_clean(path) -> bool:
    """True when ``path`` is tracked by git and has no uncommitted change."""
    from bitsignal.config import REPO_ROOT

    root = str(REPO_ROOT)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root, capture_output=True)
    if tracked.returncode != 0:
        return False
    status = subprocess.run(["git", "status", "--porcelain", "--", str(path)], cwd=root, capture_output=True, text=True)
    return status.stdout.strip() == ""


def _set_frozen_pointer(config_path, rel_path: str) -> None:
    """Point ``backtest.frozen_params`` to the frozen file, editing only that line (keeps comments)."""
    lines = io.open(config_path, encoding="utf-8").read().split("\n")
    for i, line in enumerate(lines):
        if line.lstrip().startswith("frozen_params:"):
            indent = line[: len(line) - len(line.lstrip())]
            comment = line[line.index("#"):] if "#" in line else ""
            lines[i] = f"{indent}frozen_params: {rel_path}" + (f"  {comment}" if comment else "")
            break
    else:
        raise RuntimeError("backtest.frozen_params not found in config")
    io.open(config_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def cmd_freeze_params(args):
    """Freeze the model parameters (S6, step 1). Never overwrites an existing freeze."""
    from datetime import datetime, timezone

    from bitsignal.config import (
        DEFAULT_CONFIG_PATH,
        REPO_ROOT,
        FrozenParams,
        load_config,
        model_hash,
        model_payload,
        repo_path,
        write_frozen_params,
    )
    from bitsignal.data.history import load_frozen_history

    now = datetime.now(timezone.utc)
    out = args.out or f"config/frozen/params_{now:%Y-%m-%d}.yaml"
    target = repo_path(out)
    if target.exists():
        print(f"[RECUSADO] {out} já existe: um congelamento nunca é sobrescrito.")
        sys.exit(1)
    if not _run_technical_tests():
        print("[RECUSADO] testes técnicos falharam; nada foi congelado.")
        sys.exit(1)
    cfg = load_config()
    history = load_frozen_history(cfg.data.csv_path)
    frozen = FrozenParams(
        frozen_at=now,
        csv_sha256=history.csv_sha256,
        model_hash=model_hash(cfg),
        model=model_payload(cfg),
        approval=None,
    )
    write_frozen_params(target, frozen)
    rel = target.relative_to(REPO_ROOT).as_posix() if target.is_relative_to(REPO_ROOT) else str(target)
    _set_frozen_pointer(getattr(args, "config_path", None) or DEFAULT_CONFIG_PATH, rel)
    print(f"[OK] Parâmetros congelados em {rel} (model_hash {frozen.model_hash[:12]}…).")
    print("     Próximo passo: commitar este arquivo e o config.yaml; só depois rodar")
    print("     `bitsignal backtest --window development --record`.")


def _record_refusal(args, cfg, frozen):
    """Reason to refuse ``--record``, or None."""
    from bitsignal.config import model_hash, repo_path

    if cfg.buys.on_reset != "none":
        return ("modelo v2: todas as janelas já foram vistas; a aprovação só vem da avaliação com dados "
                "futuros (bitsignal forward-eval).")
    if args.window != "development":
        return "--record só vale com --window development."
    if frozen is None:
        return "não há arquivo de parâmetros congelados (rode freeze-params primeiro)."
    if frozen.approval is not None:
        return "o approval já foi gravado; a avaliação da janela de desenvolvimento (2019+) é gravada uma única vez."
    if frozen.model_hash != model_hash(cfg):
        return "os parâmetros em uso diferem dos congelados (model_hash)."
    if not _git_committed_clean(repo_path(cfg.backtest.frozen_params)):
        return "o arquivo congelado não está commitado (ou tem alterações); commite antes do --record."
    return None


def _write_approval(cfg, frozen, report):
    from datetime import datetime, timezone

    from bitsignal.config import Approval, repo_path, write_frozen_params

    approval = Approval(
        run_at=datetime.now(timezone.utc),
        window="development",
        passed=report.criteria["passed"],
        values=report.criteria["values"],
    )
    path = repo_path(cfg.backtest.frozen_params)
    write_frozen_params(path, frozen.model_copy(update={"approval": approval}))
    print("")
    print(f"[OK] Resultado da janela de desenvolvimento (2019+) gravado em {cfg.backtest.frozen_params}. Commite este arquivo.")


def cmd_evaluate(args):
    """S7: print the verdict of the latest closed week from live CoinMetrics data."""
    from datetime import datetime, timezone

    from bitsignal.data.coinmetrics import fetch_coinmetrics
    from bitsignal.data.history import from_frame
    from bitsignal.engine.cycle import latest_verdict
    from bitsignal.engine.pipeline import run_model

    cfg = _load_cfg(args)
    history = from_frame(fetch_coinmetrics(), source="coinmetrics_live")
    result = run_model(history, cfg)
    v = latest_verdict(result, datetime.now(timezone.utc), cfg)
    print(f"Semana {v.week} · dados: {v.data_status.label}")
    if v.phase is None:
        print(f"Sem veredito: {v.reason}")
        return
    if v.buy_all_cash:
        buy = "todo o caixa disponível (inclui o produto das vendas)"
    else:
        buy = ("—" if v.buy_pct is None else f"{v.buy_pct * 100:.0f}%") + " da reserva-base"
    print(f"Fase: {v.phase.label} · venda acumulada-alvo: {v.sell_target * 100:.0f}% da posição-base "
          f"(ciclo iniciado em {v.cycle_start_date}) · compra: {buy}")
    print(f"Motivo: {v.reason}")
    print("Eventos do ciclo:")
    for e in result.events:
        if e.date >= v.cycle_start_date:
            print(f"  {e.date} {e.type.value:<18} {e.mechanism:<9} {e.note}")
    print("Painel experimental: os percentuais são referências do modelo, não ordens.")


def _now_utc():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def cmd_record_verdict(args):
    """Append the latest closed week's verdict to the weekly log (forward validation).

    Exit 1 without writing when the data is stale or the source fails, so the scheduled job
    shows the failure instead of recording a week without a verdict.
    """
    from bitsignal.config import repo_path
    from bitsignal.data.coinmetrics import fetch_coinmetrics
    from bitsignal.data.history import from_frame
    from bitsignal.engine.cycle import latest_verdict
    from bitsignal.engine.pipeline import run_model
    from bitsignal.verdict_log import append_verdict, last_recorded_hash, verdict_row

    cfg = _load_cfg(args)
    now = _now_utc()
    history = from_frame(fetch_coinmetrics(), source="coinmetrics_live")
    result = run_model(history, cfg)
    v = latest_verdict(result, now, cfg)
    if v.phase is None:
        print(f"[ERRO] Semana {v.week}: sem veredito ({v.reason}). Nada gravado.")
        sys.exit(1)
    path = repo_path(args.out or cfg.data.verdict_log_path)
    logged = last_recorded_hash(path)
    if logged is not None and logged != result.model_hash:
        print(f"[ERRO] {path} registra outro modelo (model_hash {logged[:12]}…); "
              f"este config é {result.model_hash[:12]}…. Nada gravado.")
        sys.exit(1)
    if append_verdict(path, verdict_row(result, v, now)):
        print(f"[OK] Semana {v.week} gravada em {path}: {v.phase.label}, "
              f"venda-alvo {v.sell_target * 100:.0f}%.")
    else:
        print(f"[OK] Semana {v.week} já estava gravada; nada mudou.")


V1_CONFIG = "config/config_v1.yaml"


def cmd_forward_eval(args):
    """Phase 3 (E4): v2 vs v1, buy-and-hold and uniform DCA from the v2 freeze date. Display only."""
    from bitsignal.backtest.forward import forward_eval, to_text
    from bitsignal.config import load_config, load_frozen_params
    from bitsignal.data.coinmetrics import fetch_coinmetrics
    from bitsignal.data.history import from_frame, load_frozen_history

    cfg_v2 = _load_cfg(args)
    cfg_v1 = load_config(V1_CONFIG)
    frozen = load_frozen_params(cfg_v2.backtest.frozen_params)
    if frozen is None:
        print("[ERRO] o v2 ainda não foi congelado (backtest.frozen_params vazio).")
        sys.exit(1)
    if args.offline:
        history = load_frozen_history(cfg_v2.data.csv_path)
    else:
        history = from_frame(fetch_coinmetrics(), source="coinmetrics_live")
    print(to_text(forward_eval(history, cfg_v2, cfg_v1, frozen.frozen_at.date())))


def cmd_ui(args):
    """Launch Streamlit dashboard through the same entrypoint used by Streamlit Cloud."""
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "streamlit_app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def cmd_fetch_history(args):
    """S3: download CoinMetrics history and write the frozen CSV + meta (offline afterwards)."""
    from bitsignal.config import load_config, repo_path
    from bitsignal.data.coinmetrics import check_catalog, fetch_coinmetrics
    from bitsignal.data.history import compare_histories, from_frame, load_frozen_history, write_frozen_history

    cfg = load_config()
    out = args.out or cfg.data.csv_path

    catalog = check_catalog()
    missing = [m for m, ok in catalog.items() if not ok]
    if missing:
        print(f"[ERRO] Métricas fora do plano Community da CoinMetrics: {missing}")
        sys.exit(1)

    df = fetch_coinmetrics()
    live = from_frame(df, source="coinmetrics_live")

    previous = repo_path(out)
    if previous.exists():
        diffs = compare_histories(live, load_frozen_history(previous))
        if diffs.empty:
            print("[OK] Histórico ao vivo igual ao CSV anterior na janela comum.")
        else:
            print(f"[AVISO] {len(diffs)} diferença(s) contra o CSV anterior (revisão da CoinMetrics?):")
            print(diffs.head(20).to_string(index=False))

    meta = write_frozen_history(df, out)
    print(f"[OK] {meta['rows']} linhas gravadas em {out} (as_of {meta['last_date']}, sha256 {meta['sha256'][:12]}…)")
    if meta["gaps"]:
        for col, dates in meta["gaps"].items():
            print(f"     lacuna em {col}: {len(dates)} dia(s), primeiro {dates[0]}")


def main():
    parser = argparse.ArgumentParser(prog="bitsignal", description="BitSignal — modelo de ciclo unificado")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_fh = subparsers.add_parser("fetch-history", help="Download CoinMetrics history into the frozen CSV")
    p_fh.add_argument("--out", default=None, help="CSV path (default: data.csv_path from config)")

    p_bt = subparsers.add_parser("backtest", help="Backtest the default model vs Q1 benchmarks (offline)")
    p_bt.add_argument("--window", choices=["calibration", "development"], default="calibration",
                      help="calibration (default, no 2019+ criteria) or development (needs frozen params)")
    p_bt.add_argument("--config", default=None, help="Config file (default: config/config.yaml)")
    p_bt.add_argument("--no-sensitivities", action="store_true", help="Skip the sensitivities")
    p_bt.add_argument("--variants", action="store_true",
                      help="Phase 2: default model plus the comparison variants (never recorded)")
    p_bt.add_argument("--record", action="store_true",
                      help="S6 only: record the single 2019+ evaluation in the frozen file")

    p_fz = subparsers.add_parser("freeze-params", help="Freeze the model parameters (S6)")
    p_fz.add_argument("--out", default=None, help="Default: config/frozen/params_<date>.yaml")

    p_ev = subparsers.add_parser("evaluate", help="Print the model verdict for the latest closed week (live data)")
    p_ev.add_argument("--config", default=None, help="Config file (default: config/config.yaml)")
    subparsers.add_parser("ui", help="Launch the Streamlit dashboard")

    p_fe = subparsers.add_parser("forward-eval", help="Phase 3: forward evaluation of v2 (display only)")
    p_fe.add_argument("--config", default=None, help="v2 config (default: config/config.yaml)")
    p_fe.add_argument("--offline", action="store_true", help="Use the frozen CSV instead of live data")

    p_rv = subparsers.add_parser("record-verdict",
                                 help="Append the latest closed week's verdict to the weekly log")
    p_rv.add_argument("--out", default=None, help="Default: data.verdict_log_path of the config")
    p_rv.add_argument("--config", default=None, help="Config file (default: config/config.yaml)")

    args = parser.parse_args()
    commands = {
        "fetch-history": cmd_fetch_history,
        "backtest": cmd_backtest,
        "freeze-params": cmd_freeze_params,
        "evaluate": cmd_evaluate,
        "ui": cmd_ui,
        "record-verdict": cmd_record_verdict,
        "forward-eval": cmd_forward_eval,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
