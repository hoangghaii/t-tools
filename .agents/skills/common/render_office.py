#!/usr/bin/env python3
"""Render Office files through an isolated LibreOffice profile, then render PDF pages."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def render(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    executable = os.environ.get('SOFFICE') or shutil.which('soffice') or shutil.which('libreoffice')
    if not executable:
        candidate = Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
        executable = str(candidate) if candidate.exists() else None
    if source.suffix.lower() != '.pdf':
        if not executable:
            raise RuntimeError('LibreOffice is required; install it or set SOFFICE.')
        with tempfile.TemporaryDirectory(prefix='agentkit-office-') as profile:
            cmd = [executable, '-env:UserInstallation=' + Path(profile).as_uri(),
                   '--headless', '--convert-to', 'pdf', '--outdir', str(output), str(source)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            pdf = output / (source.stem + '.pdf')
            if result.returncode or not pdf.exists():
                raise RuntimeError('Office render failed: ' + (result.stderr or result.stdout))
    else:
        pdf = source
    import pymupdf
    with pymupdf.open(pdf) as document:
        for index, page in enumerate(document):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(output / f'page-{index+1}.png')
        return len(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    print(f'Rendered {render(args.source, args.output)} pages')


if __name__ == '__main__':
    main()
