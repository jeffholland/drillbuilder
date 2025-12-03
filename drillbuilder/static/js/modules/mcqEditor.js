// MCQ Editor functionality
export function initMCQEditor(token, quizId, hideAllEditors, loadQuiz) {
  // Store original save function
  const saveMcqOriginal = async () => {
    const prompt = document.getElementById('mcqPrompt').value.trim();
    if (!prompt) { alert('Question text required'); return; }
    
    const questionImageUrl = document.getElementById('mcqQuestionImageUrl').value || null;
    
    const choices = Array.from(document.querySelectorAll('.mcq-choice')).map(c => ({
      text: c.querySelector('.mcq-text').value.trim(),
      is_correct: c.querySelector('.mcq-correct').checked,
      image_url: c.querySelector('.choice-image-url').value || null
    }));
    if (choices.length < 2) { alert('At least 2 choices required'); return; }
    if (!choices.some(c => c.is_correct)) { alert('Mark at least one choice as correct'); return; }

    const payload = {
      type: 'multiple_choice',
      prompt_text: prompt,
      prompt_image_url: questionImageUrl,
      mcq_options: choices
    };
    const r = await fetch(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(payload)
    });
    if (r.status === 201) {
      resetMcqEditor();
      hideAllEditors();
      loadQuiz();
    } else {
      alert('Failed to save MCQ');
    }
  };

  function resetMcqEditor() {
    document.getElementById('mcqPrompt').value = '';
    document.getElementById('mcqQuestionImageUrl').value = '';
    document.getElementById('mcqQuestionImagePreview').innerHTML = '';
    document.getElementById('mcqChoices').innerHTML = `
      <div class="mcq-choice">
        <input type="text" placeholder="Choice 1" class="mcq-text" />
        <label><input type="checkbox" class="mcq-correct" /> Correct</label>
        <button type="button" class="choice-image-btn" onclick="window.imageUpload.triggerImageUpload(this.parentElement.querySelector('.choice-image-input'))" style="font-size:11px;padding:2px 6px;margin-left:8px;">📷</button>
        <input type="file" class="choice-image-input" accept=".jpg,.jpeg" style="display:none" onchange="window.handleChoiceImageUpload(this)" />
        <input type="hidden" class="choice-image-url" />
        <div class="choice-image-preview" style="display:inline-block;margin-left:5px;"></div>
      </div>
      <div class="mcq-choice">
        <input type="text" placeholder="Choice 2" class="mcq-text" />
        <label><input type="checkbox" class="mcq-correct" /> Correct</label>
        <button type="button" class="choice-image-btn" onclick="window.imageUpload.triggerImageUpload(this.parentElement.querySelector('.choice-image-input'))" style="font-size:11px;padding:2px 6px;margin-left:8px;">📷</button>
        <input type="file" class="choice-image-input" accept=".jpg,.jpeg" style="display:none" onchange="window.handleChoiceImageUpload(this)" />
        <input type="hidden" class="choice-image-url" />
        <div class="choice-image-preview" style="display:inline-block;margin-left:5px;"></div>
      </div>
    `;
    
    // Reset save button
    const saveBtn = document.getElementById('saveMcq');
    saveBtn.innerText = 'Save MCQ';
    saveBtn.onclick = saveMcqOriginal;
  }

  function updateDeleteButtons() {
    const choices = document.querySelectorAll('.mcq-choice');
    choices.forEach(c => {
      let btn = c.querySelector('.delete-choice');
      
      // Create delete button if it doesn't exist
      if (!btn) {
        btn = document.createElement('button');
        btn.className = 'delete-choice';
        btn.style.marginLeft = '10px';
        btn.innerText = 'Delete';
        c.appendChild(btn);
      }
      
      // Show/hide based on number of choices
      if (choices.length > 2) {
        btn.style.display = 'inline';
        btn.onclick = () => { c.remove(); updateDeleteButtons(); };
      } else {
        btn.style.display = 'none';
      }
    });
  }

  // Add MCQ Choice button
  document.getElementById('addMcqChoice').onclick = () => {
    const container = document.getElementById('mcqChoices');
    const div = document.createElement('div');
    div.className = 'mcq-choice';
    div.innerHTML = `
      <input type="text" placeholder="Choice" class="mcq-text" />
      <label><input type="checkbox" class="mcq-correct" /> Correct</label>
      <button type="button" class="choice-image-btn" onclick="window.imageUpload.triggerImageUpload(this.parentElement.querySelector('.choice-image-input'))" style="font-size:11px;padding:2px 6px;margin-left:8px;">📷</button>
      <input type="file" class="choice-image-input" accept=".jpg,.jpeg" style="display:none;" onchange="window.handleChoiceImageUpload(this)" />
      <input type="hidden" class="choice-image-url" />
      <div class="choice-image-preview" style="display:inline-block;margin-left:5px;"></div>
      <button class="delete-choice" style="margin-left:10px">Delete</button>
    `;
    container.appendChild(div);
    updateDeleteButtons();
  };

  document.getElementById('saveMcq').onclick = saveMcqOriginal;
  document.getElementById('cancelMcq').onclick = () => hideAllEditors();

  return { resetMcqEditor, updateDeleteButtons, saveMcqOriginal };
}

export async function updateMcq(questionId, token, quizId, resetMcqEditor, hideAllEditors, loadQuiz) {
  const prompt = document.getElementById('mcqPrompt').value.trim();
  if (!prompt) { alert('Question text required'); return; }
  
  const questionImageUrl = document.getElementById('mcqQuestionImageUrl').value || null;
  
  const choices = Array.from(document.querySelectorAll('.mcq-choice')).map(c => ({
    text: c.querySelector('.mcq-text').value.trim(),
    is_correct: c.querySelector('.mcq-correct').checked,
    image_url: c.querySelector('.choice-image-url').value || null
  }));
  if (choices.length < 2) { alert('At least 2 choices required'); return; }
  if (!choices.some(c => c.is_correct)) { alert('Mark at least one choice as correct'); return; }

  // Delete old question and create new one (simpler than updating)
  const delR = await fetch(`/quizzes/${quizId}/questions/${questionId}`, {
    method: 'DELETE',
    headers: {'Authorization': 'Bearer ' + token}
  });
  
  if (delR.ok) {
    const payload = {
      type: 'multiple_choice',
      prompt_text: prompt,
      prompt_image_url: questionImageUrl,
      mcq_options: choices
    };
    const r = await fetch(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(payload)
    });
    if (r.status === 201) {
      resetMcqEditor();
      hideAllEditors();
      loadQuiz();
    } else {
      alert('Failed to update MCQ');
    }
  } else {
    alert('Failed to delete old question');
  }
}
