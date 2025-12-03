// Quiz loading and rendering
export async function loadQuiz(quizId, token, renderQuestions) {
  const r = await fetch(`/quizzes/${quizId}`, {headers: {'Authorization': 'Bearer ' + token}});
  const quiz = await r.json();
  document.getElementById('quizTitle').innerText = quiz.title || '';
  renderQuestions(quiz.questions || []);
}

export function renderQuestions(questions, setAllQuestions) {
  setAllQuestions(questions);
  const node = document.getElementById('questionsList');
  if (!questions.length) {
    node.innerHTML = '<p>No questions yet. Add one below!</p>';
  } else {
    node.innerHTML = questions.map((q, idx) => 
      `<div class="card"><strong>Q${idx+1}:</strong> ${q.prompt_text} <small>(${q.type})</small> <button onclick="window.editQuestion(${q.id})" style="margin-left:10px;">Edit</button> <button onclick="window.deleteQuestion(${q.id})" style="margin-left:5px;">Delete</button></div>`
    ).join('');
  }
}

export async function deleteQuestion(questionId, quizId, token, loadQuiz) {
  if (!confirm('Delete this question?')) return;
  
  const r = await fetch(`/quizzes/${quizId}/questions/${questionId}`, {
    method: 'DELETE',
    headers: {'Authorization': 'Bearer ' + token}
  });
  
  if (r.ok) {
    loadQuiz();
  } else {
    alert('Failed to delete question');
  }
}

export function hideAllEditors() {
  document.getElementById('mcqEditor').style.display = 'none';
  document.getElementById('clozeEditor').style.display = 'none';
  document.getElementById('wordMatchEditor').style.display = 'none';
}
