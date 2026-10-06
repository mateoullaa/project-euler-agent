#!/usr/bin/env python3
"""
Project Euler AI Agent - Instituto Tecnico Renault
Autonomous agent with self-correction retry loop to solve Project Euler problems (9 to 20).
"""

import os
import sys
import time
import json
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Error: 'google-genai' library not found. Install with: pip install google-genai")
    sys.exit(1)


# Ground truth for automatic verification mode (--auto-verify)
GROUND_TRUTH = {
    9: "31875000",
    10: "142913828922",
    11: "70600674",
    12: "76576500",
    13: "5537376230",
    14: "837799",
    15: "137846528820",
    16: "1366",
    17: "21124",
    18: "1074",
    19: "171",
    20: "648",
}


class Problem:
    def __init__(self, number: int, title: str, full_text: str):
        self.number = number
        self.title = title
        self.full_text = full_text

    def __repr__(self):
        return f"<Problem {self.number}: {self.title}>"


def parse_problems_file(filepath: Path) -> dict[int, Problem]:
    """Parse problems.txt into a dictionary of Problem objects."""
    if not filepath.exists():
        raise FileNotFoundError(f"Problems file not found: {filepath}")

    content = filepath.read_text(encoding="utf-8")
    
    # Regex matching Problem header: Problem X: Title
    pattern = re.compile(
        r"[-=]+\s*\nProblem\s+(\d+):\s*([^\n]+)\s*\n[-=]+(.*?)(?=(?:[-=]+\s*\nProblem\s+\d+:|={5,}|$))",
        re.DOTALL
    )
    
    problems = {}
    for match in pattern.finditer(content):
        num = int(match.group(1))
        title = match.group(2).strip()
        body = match.group(3).strip()
        full_text = f"Problem {num}: {title}\n\n{body}"
        problems[num] = Problem(num, title, full_text)

    return problems


def extract_code(text: str) -> str:
    """Extract Python code block from markdown output."""
    match = re.search(r"```python(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


class EulerAgent:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.5-flash-lite",
        max_attempts: int = 5,
        timeout: int = 30,
        auto_verify: bool = False,
        base_dir: Path | None = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.auto_verify = auto_verify
        self.base_dir = base_dir or Path(__file__).resolve().parent

        self.solutions_dir = self.base_dir / "solutions"
        self.logs_dir = self.base_dir / "logs"
        self.scratch_dir = self.base_dir / "scratch"

        self.solutions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.logs_dir / "agent_attempts.log"
        self.json_log_file = self.logs_dir / "attempts.json"
        
        self.all_attempts_record = []
        if self.json_log_file.exists():
            try:
                self.all_attempts_record = json.loads(self.json_log_file.read_text(encoding="utf-8"))
            except Exception:
                self.all_attempts_record = []

        self.client = genai.Client(api_key=self.api_key)

    def log_attempt(
        self,
        problem_num: int,
        title: str,
        attempt: int,
        code: str,
        output: str,
        error: str | None,
        runtime: float,
        result: str,
    ):
        """Append attempt record to human-readable log and structured JSON."""
        timestamp = datetime.now().isoformat()
        
        entry = {
            "problem": problem_num,
            "title": title,
            "attempt": attempt,
            "timestamp": timestamp,
            "runtime_seconds": round(runtime, 4),
            "result": result,
            "output": output.strip(),
            "error": error.strip() if error else None,
            "code": code,
        }
        self.all_attempts_record.append(entry)
        self.json_log_file.write_text(json.dumps(self.all_attempts_record, indent=2, ensure_ascii=False), encoding="utf-8")

        # Text log
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"Problem {problem_num}: {title} | Attempt {attempt}/{self.max_attempts}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Execution Time: {runtime:.4f}s | Result: {result}\n")
            f.write("-" * 80 + "\n")
            f.write("GENERATED CODE:\n")
            f.write(code + "\n")
            f.write("-" * 80 + "\n")
            f.write(f"STDOUT OUTPUT:\n{output.strip()}\n")
            if error:
                f.write(f"STDERR / ERROR:\n{error.strip()}\n")
            f.write("=" * 80 + "\n\n")

    def call_gemini(self, prompt: str) -> str:
        """Call Gemini model with retry on temporary errors."""
        models_to_try = [self.model_name, "gemini-3.5-flash", "gemini-3.8-flash"]
        last_exception = None

        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                if response.text:
                    return response.text
            except Exception as e:
                last_exception = e
                time.sleep(2)
                continue

        raise RuntimeError(f"Failed to get response from Gemini models: {last_exception}")

    def execute_code(self, code: str, problem_num: int, attempt: int) -> tuple[str, str | None, float, bool]:
        """
        Execute python script in subprocess with timeout.
        Returns: (stdout, stderr, runtime_seconds, success_flag)
        """
        script_file = self.scratch_dir / f"p{problem_num:02d}_try{attempt}.py"
        script_file.write_text(code, encoding="utf-8")

        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            runtime = time.perf_counter() - start_time
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()

            if res.returncode == 0:
                return stdout, None, runtime, True
            else:
                return stdout, f"RuntimeError (exit code {res.returncode}):\n{stderr}", runtime, False

        except subprocess.TimeoutExpired:
            runtime = time.perf_counter() - start_time
            return "", f"TimeoutExpired: Execution exceeded limit of {self.timeout} seconds.", runtime, False
        except Exception as e:
            runtime = time.perf_counter() - start_time
            return "", f"Execution Exception: {str(e)}", runtime, False

    def solve_problem(self, problem: Problem) -> bool:
        """Execute autonomous cycle for a single problem."""
        print(f"\n==================================================")
        print(f"Solving Problem {problem.number}: {problem.title}")
        print(f"==================================================")

        attempt = 1
        previous_code = ""
        previous_error = ""
        
        while attempt <= self.max_attempts:
            print(f"-> Attempt {attempt}/{self.max_attempts} for Problem {problem.number}...")

            # Construct prompt
            if attempt == 1:
                prompt = f"""You are an expert Python algorithm developer solving Project Euler Problem {problem.number}.

Problem Statement:
{problem.full_text}

Instructions:
1. Write a self-contained, clean, highly optimized Python script that calculates the exact answer.
2. Use ONLY the Python standard library (no external third-party packages).
3. Any data given in the problem (e.g. grids, triangles, 50-digit numbers) MUST be embedded directly in the Python script.
4. The script MUST calculate the answer and print ONLY the final answer to stdout using: print(answer)
5. Return your Python script inside a single ```python ... ``` markdown block.
"""
            else:
                prompt = f"""You are an expert Python algorithm developer fixing Project Euler Problem {problem.number}.

Original Problem Statement:
{problem.full_text}

Your previous code in attempt {attempt - 1} was:
```python
{previous_code}
```

The execution resulted in the following issue:
{previous_error}

Instructions:
1. Analyze carefully what went wrong (syntax error, logic flaw, performance/timeout, off-by-one, or wrong edge case).
2. Write a fully corrected, highly optimized, and robust Python script.
3. The script MUST print ONLY the final answer to stdout using: print(answer)
4. Return ONLY the complete corrected Python code inside a ```python ... ``` block.
"""

            # 1. Ask Gemini
            print("   Asking Gemini for Python code...")
            try:
                raw_response = self.call_gemini(prompt)
                code = extract_code(raw_response)
            except Exception as e:
                err_msg = f"Gemini API Error: {e}"
                print(f"   {err_msg}")
                self.log_attempt(
                    problem.number, problem.title, attempt, "", "", err_msg, 0.0, "API_ERROR"
                )
                attempt += 1
                previous_error = err_msg
                time.sleep(2)
                continue

            # 2. Execute code
            print(f"   Executing generated code (timeout: {self.timeout}s)...")
            stdout, stderr, runtime, success = self.execute_code(code, problem.number, attempt)
            previous_code = code

            if not success:
                print(f"   Execution failed ({runtime:.2f}s): {stderr.splitlines()[0] if stderr else 'Error'}")
                self.log_attempt(
                    problem.number, problem.title, attempt, code, stdout, stderr, runtime, "EXECUTION_ERROR"
                )
                previous_error = f"Execution failed:\n{stderr}"
                attempt += 1
                continue

            # Extract answer (last non-empty line of stdout)
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            candidate_answer = lines[-1] if lines else ""
            print(f"   Execution succeeded in {runtime:.4f}s. Output: {candidate_answer}")

            # 3. Verify answer
            is_verified = False
            if self.auto_verify:
                expected = GROUND_TRUTH.get(problem.number)
                if expected and candidate_answer == expected:
                    is_verified = True
                    print(f"   [AUTO-VERIFY] Correct! ({candidate_answer} == {expected})")
                else:
                    print(f"   [AUTO-VERIFY] Incorrect output: got '{candidate_answer}', expected '{expected}'.")
                    previous_error = (
                        f"The code ran without error and outputted '{candidate_answer}', "
                        f"but this answer is INCORRECT on Project Euler. "
                        f"Please re-read the problem statement, check the exact constraints, "
                        f"off-by-one errors, and algorithm logic."
                    )
            else:
                # Manual interactive verification
                print("\n   -------------------------------------------------")
                print(f"   [VERIFICATION NEEDED] Problem {problem.number} candidate answer: {candidate_answer}")
                print("   Enter 'ok' / 'y' if verified on Project Euler.")
                print("   Or enter feedback / error message to trigger a retry:")
                user_feedback = input("   Verification feedback: ").strip()
                print("   -------------------------------------------------")

                if user_feedback.lower() in ("ok", "y", "yes", "correct", "true"):
                    is_verified = True
                else:
                    feedback_str = user_feedback if user_feedback else "Incorrect answer on Project Euler."
                    previous_error = f"Project Euler verification failed: {feedback_str}. Output was '{candidate_answer}'."

            if is_verified:
                # Save attempt log
                self.log_attempt(
                    problem.number, problem.title, attempt, code, stdout, None, runtime, "SUCCESS"
                )
                # Save final solution file
                solution_path = self.solutions_dir / f"problem_{problem.number:02d}.py"
                header = (
                    f'"""\nProject Euler - Problem {problem.number}: {problem.title}\n'
                    f'Answer: {candidate_answer}\n'
                    f'Resolved on Attempt: {attempt} in {runtime:.4f}s\n'
                    f'Generated by Gemini AI Agent\n"""\n\n'
                )
                solution_path.write_text(header + code, encoding="utf-8")
                print(f"   Saved final solution to: {solution_path}")
                return True
            else:
                self.log_attempt(
                    problem.number, problem.title, attempt, code, stdout, previous_error, runtime, "INCORRECT_ANSWER"
                )
                attempt += 1

        print(f"FAILED: Reached maximum {self.max_attempts} attempts for Problem {problem.number}.")
        return False

    def run(self, problems: list[Problem]):
        """Run agent over a list of problems."""
        print(f"Starting Project Euler AI Agent | {len(problems)} problem(s) queued.")
        print(f"Model: {self.model_name} | Max attempts: {self.max_attempts} | Timeout: {self.timeout}s")
        print(f"Mode: {'AUTOMATIC (GROUND TRUTH)' if self.auto_verify else 'MANUAL INTERACTIVE'}")
        
        start_all = time.perf_counter()
        results = {}

        for p in problems:
            success = self.solve_problem(p)
            results[p.number] = success

        total_time = time.perf_counter() - start_all
        solved_count = sum(1 for v in results.values() if v)

        print("\n" + "=" * 50)
        print("AGENT EXECUTION SUMMARY")
        print("=" * 50)
        print(f"Total problems: {len(problems)}")
        print(f"Solved: {solved_count}/{len(problems)} ({solved_count / len(problems) * 100:.1f}%)")
        print(f"Total time elapsed: {total_time:.2f}s")
        for num, status in sorted(results.items()):
            print(f"  Problem {num:2d}: {'[SOLVED]' if status else '[FAILED]'}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Project Euler AI Agent")
    parser.add_argument(
        "--problems",
        type=str,
        default="9-20",
        help="Range or comma-separated list of problems, e.g. '9-20' or '9,10,15'",
    )
    parser.add_argument(
        "--problems-file",
        type=str,
        default=None,
        help="Path to problems.txt file",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Gemini API key (defaults to GEMINI_API_KEY env var or gemini_api_key.txt)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.5-flash-lite",
        help="Gemini model name (default: gemini-3.5-flash-lite)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximum attempts per problem (default: 5)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds per execution (default: 30)",
    )
    parser.add_argument(
        "--auto-verify",
        action="store_true",
        help="Automatically verify answers against ground truth (ideal for batch execution)",
    )

    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).resolve().parent
    problems_path = Path(args.problems_file) if args.problems_file else base_dir / "problems.txt"

    # Resolve API Key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        key_file = base_dir / "gemini_api_key.txt"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()

    if not api_key:
        print("Error: No Gemini API key provided. Set GEMINI_API_KEY, use --api-key, or create gemini_api_key.txt.")
        sys.exit(1)

    # Parse problems
    all_problems = parse_problems_file(problems_path)

    # Filter requested problems
    target_numbers = []
    if "-" in args.problems:
        start, end = map(int, args.problems.split("-"))
        target_numbers = list(range(start, end + 1))
    else:
        target_numbers = [int(x.strip()) for x in args.problems.split(",") if x.strip()]

    selected_problems = [all_problems[n] for n in target_numbers if n in all_problems]

    if not selected_problems:
        print(f"Error: No matching problems found for selection '{args.problems}'.")
        sys.exit(1)

    agent = EulerAgent(
        api_key=api_key,
        model_name=args.model,
        max_attempts=args.max_attempts,
        timeout=args.timeout,
        auto_verify=args.auto_verify,
        base_dir=base_dir,
    )

    agent.run(selected_problems)


if __name__ == "__main__":
    main()
