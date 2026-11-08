"""Offline model rebuild. Existing artifacts are verified, never overwritten."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("conditional_model", ROOT/"dashboard/conditional_model.py")
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Source requests are disabled during the conditional model rebuild")


def rebuild(config=model.CONFIG, output=model.ARTIFACT, check=False, with_published=False):
    published = None
    if with_published:
        spec = importlib.util.spec_from_file_location("saved_rebuild", ROOT/"analysis/23_rebuild_published_results.py")
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        published = producer.rebuild(check)
    raw = model.json_bytes(model.report(config))
    if output.exists():
        model.require(output.read_bytes() == raw, f"Generated-file mismatch: {output}; use an unused --output for a changed scenario")
    else:
        model.require(not check, f"Missing model artifact: {output}")
        # Never allow a scenario output to overwrite a saved input or existing file.
        with output.open("xb") as handle:
            handle.write(raw)
    return {"model_artifact": str(output), "verified": True, "source_requests": 0, "published_evidence": published}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=model.CONFIG)
    parser.add_argument("--output", type=Path, default=model.ARTIFACT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--with-published", action="store_true", help="Also run the existing saved-input published-results rebuild")
    args = parser.parse_args(argv)
    sys.addaudithook(deny_network)
    try:
        print(json.dumps(rebuild(args.assumptions,args.output,args.check,args.with_published),indent=2))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print(f"Model rebuild stopped: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
