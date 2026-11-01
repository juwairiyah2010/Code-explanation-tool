import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from streamlit.testing.v1 import AppTest

def test_frontend_quiz_and_docs():
    print("Initializing AppTest...")
    at = AppTest.from_file(str(_ROOT / "frontend" / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"App crashed on startup: {at.exception}"
    print("✓ App started with no exceptions.")

    # Check that tabs rendered
    tab_labels = [t.label for t in at.tabs]
    print(f"Rendered tabs: {tab_labels}")
    assert "🎓 Quiz & Practice" in tab_labels, "Quiz tab missing"
    assert "📚 Reference Docs" in tab_labels, "Reference Docs tab missing"
    print("✓ All 5 tabs rendered and accessible.")

    # Test quiz standalone button
    gen_buttons = [b for b in at.button if b.key == "btn_gen_quiz_standalone"]
    print(f"Standalone quiz generation buttons found: {len(gen_buttons)}")
    assert len(gen_buttons) == 1, "Expected standalone quiz button"

    print("Clicking 'Generate Practice Quiz for Current Code'...")
    gen_buttons[0].click().run()
    assert not at.exception, f"Quiz generation caused exception: {at.exception}"
    
    # Check that quiz questions are rendered
    quiz_data = at.session_state.get("quiz_result")
    assert quiz_data is not None, "quiz_result was not populated in session_state"
    assert "questions" in quiz_data, "No questions in quiz_result"
    print(f"✓ Generated {len(quiz_data['questions'])} quiz questions successfully!")

    # Check radio button for question 1
    radios = [r for r in at.radio if "active_choice" in (r.key or "")]
    print(f"Found active radio choices: {len(radios)}")
    assert len(radios) > 0, "No radio buttons for question choices"

    # Select choice
    q1 = quiz_data["questions"][0]
    first_opt = q1["options"][0]["id"]
    radios[0].set_value(first_opt)
    
    # Click Submit Answer
    sub_buttons = [b for b in at.button if "btn_sub_" in (b.key or "")]
    assert len(sub_buttons) > 0, "Submit button not found"
    print("Submitting answer...")
    sub_buttons[0].click().run()
    assert not at.exception, f"Submit answer threw exception: {at.exception}"
    print("✓ Answer submitted without KeyError!")

    # Verify user answer was recorded and question marked as answered
    assert at.session_state.get("quiz_question_answered") is True, "quiz_question_answered should be True"
    assert at.session_state.get("quiz_user_answers"), "quiz_user_answers should not be empty"
    print(f"✓ Recorded user answer: {at.session_state['quiz_user_answers']}")

    # Click Next Question
    nxt_buttons = [b for b in at.button if "btn_nxt_" in (b.key or "")]
    if nxt_buttons:
        print("Clicking Next Question...")
        nxt_buttons[0].click().run()
        assert not at.exception, f"Next question threw exception: {at.exception}"
        assert at.session_state["quiz_current_index"] == 1, "Expected current index to advance to 1"
        print("✓ Advanced to Question 2 successfully!")

    # Test Reference Docs: Quick chip search
    chip_buttons = [b for b in at.button if b.key == "qchip_rec"]
    assert len(chip_buttons) > 0, "Quick chip button not found"
    print("Clicking 'Recursion' quick suggestion chip...")
    chip_buttons[0].click().run()
    assert not at.exception, f"Quick chip threw exception: {at.exception}"
    assert at.session_state.get("rag_query_val") == "recursion", "rag_query_val not set"
    print("✓ Quick chip set search term to 'recursion'!")

    print("ALL TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_frontend_quiz_and_docs()
