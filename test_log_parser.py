import unittest

from parser import analyze_log


class AnalyzeLogTests(unittest.TestCase):
    def test_groups_python_traceback_into_one_crash_finding(self) -> None:
        log = "\n".join(
            [
                "WARNING:root:transient failure",
                "Traceback (most recent call last):",
                '  File "/app/main.py", line 8, in <module>',
                "    run()",
                'ValueError: invalid value',
            ]
        )

        result = analyze_log(log, "python")

        self.assertEqual(result["summary"]["warnings"], 1)
        self.assertEqual(result["summary"]["crashes"], 1)
        self.assertEqual(result["crash_types"]["exception_traceback"], 1)
        crash_finding = result["findings"][1]
        self.assertEqual(crash_finding["line_number"], 2)
        self.assertEqual(crash_finding["end_line_number"], 5)
        self.assertEqual(crash_finding["message"], "ValueError: invalid value")
        self.assertIn('File "/app/main.py"', crash_finding["context"])

    def test_groups_cpp_linker_failure_into_one_crash_finding(self) -> None:
        log = "\n".join(
            [
                "main.cpp:12: warning: narrowing conversion",
                "ld: undefined reference to `Widget::run()`",
                "collect2: error: ld returned 1 exit status",
            ]
        )

        result = analyze_log(log, "c_cpp")

        self.assertEqual(result["summary"]["warnings"], 1)
        self.assertEqual(result["summary"]["crashes"], 1)
        self.assertEqual(result["crash_types"]["undefined_reference"], 1)
        crash_finding = result["findings"][1]
        self.assertEqual(crash_finding["line_number"], 2)
        self.assertEqual(crash_finding["end_line_number"], 3)
        self.assertIn("collect2: error", crash_finding["context"])

    def test_keeps_distinct_cpp_crashes_separate(self) -> None:
        log = "\n".join(
            [
                "Segmentation fault (core dumped)",
                "",
                "stack smashing detected",
            ]
        )

        result = analyze_log(log, "c_cpp")

        self.assertEqual(result["summary"]["crashes"], 2)
        self.assertEqual(result["crash_types"]["segmentation_fault"], 1)
        self.assertEqual(result["crash_types"]["stack_smashing"], 1)

    def test_groups_asan_report_and_classifies_it(self) -> None:
        log = "\n".join(
            [
                "AddressSanitizer:DEADLYSIGNAL",
                "=================================================================",
                "==167744==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000030",
                "==167744==The signal is caused by a READ memory access.",
                "    #0 0x55f78abcb165 in example() /src/example.cxx:851:15",
                "SUMMARY: AddressSanitizer: SEGV /src/example.cxx:851:15 in example()",
                "==167744==ABORTING",
            ]
        )

        result = analyze_log(log, "c_cpp")

        self.assertEqual(result["summary"]["crashes"], 1)
        self.assertEqual(result["crash_types"]["asan_segv"], 1)
        crash_finding = result["findings"][0]
        self.assertEqual(crash_finding["line_number"], 1)
        self.assertEqual(crash_finding["end_line_number"], 7)
        self.assertEqual(
            crash_finding["message"],
            "SUMMARY: AddressSanitizer: SEGV /src/example.cxx:851:15 in example()",
        )
        self.assertIn("#0 0x55f78abcb165 in example()", crash_finding["context"])

    def test_auto_detects_asan_as_c_cpp(self) -> None:
        log = "\n".join(
            [
                "AddressSanitizer:DEADLYSIGNAL",
                "==123==ERROR: AddressSanitizer: heap-use-after-free on address 0x603000000040",
            ]
        )

        result = analyze_log(log)

        self.assertEqual(result["language"], "c_cpp")
        self.assertEqual(result["crash_types"]["asan_heap_use_after_free"], 1)

    def test_auto_detects_python(self) -> None:
        log = "\n".join(
            [
                "Traceback (most recent call last):",
                "ModuleNotFoundError: No module named 'app'",
            ]
        )

        result = analyze_log(log)

        self.assertEqual(result["language"], "python")


if __name__ == "__main__":
    unittest.main()
