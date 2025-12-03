// Word Match Editor functionality
export function initWordMatchEditor(token, quizId, hideAllEditors, loadQuiz) {
  function resetWordMatchEditor() {
    document.getElementById('wmQuestionImageUrl').value = '';
    document.getElementById('wmQuestionImagePreview').innerHTML = '';
    document.getElementById('wordMatchPairs').innerHTML = `
      <div class="word-match-pair">
        <input type="text" placeholder="Left word" class="wm-left" />
        <button type="button" onclick="window.imageUpload.triggerWMImageUpload(this, 'left')" style="font-size:11px;padding:2px 6px;margin:0 5px;">📷</button>
        <span> → </span>
        <input type="text" placeholder="Right word" class="wm-right" />
        <button type="button" onclick="window.imageUpload.triggerWMImageUpload(this, 'right')" style="font-size:11px;padding:2px 6px;margin:0 5px;">📷</button>
        <input type="file" class="wm-left-image-input" accept=".jpg,.jpeg" style="display:none;" onchange="window.handleWMImageUpload(this, 'left')" />
        <input type="hidden" class="wm-left-image-url" />
        <input type="file" class="wm-right-image-input" accept=".jpg,.jpeg" style="display:none;" onchange="window.handleWMImageUpload(this, 'right')" />
        <input type="hidden" class="wm-right-image-url" />
        <div class="wm-left-preview" style="display:inline-block;margin-left:5px;"></div>
        <div class="wm-right-preview" style="display:inline-block;margin-left:5px;"></div>
      </div>
    `;
    const saveBtn = document.getElementById('saveWordMatch');
    saveBtn.innerText = 'Save Word Match';
    saveBtn.onclick = saveWordMatch;
  }
  
  function updateWordPairDelete() {
    const pairs = document.querySelectorAll('.word-match-pair');
    pairs.forEach(p => {
      const btn = p.querySelector('.delete-pair');
      if (pairs.length > 1 && btn) {
        btn.style.display = 'inline';
        btn.onclick = () => { p.remove(); updateWordPairDelete(); };
      } else if (btn) {
        btn.style.display = 'none';
      }
    });
  }

  document.getElementById('addWordPair').onclick = () => {
    const container = document.getElementById('wordMatchPairs');
    const div = document.createElement('div');
    div.className = 'word-match-pair';
    div.innerHTML = `
      <input type="text" placeholder="Left word" class="wm-left" />
      <button type="button" onclick="window.imageUpload.triggerWMImageUpload(this, 'left')" style="font-size:11px;padding:2px 6px;margin:0 5px;">📷</button>
      <span> → </span>
      <input type="text" placeholder="Right word" class="wm-right" />
      <button type="button" onclick="window.imageUpload.triggerWMImageUpload(this, 'right')" style="font-size:11px;padding:2px 6px;margin:0 5px;">📷</button>
      <input type="file" class="wm-left-image-input" accept=".jpg,.jpeg" style="display:none;" onchange="window.handleWMImageUpload(this, 'left')" />
      <input type="hidden" class="wm-left-image-url" />
      <input type="file" class="wm-right-image-input" accept=".jpg,.jpeg" style="display:none;" onchange="window.handleWMImageUpload(this, 'right')" />
      <input type="hidden" class="wm-right-image-url" />
      <div class="wm-left-preview" style="display:inline-block;margin-left:5px;"></div>
      <div class="wm-right-preview" style="display:inline-block;margin-left:5px;"></div>
      <button class="delete-pair" style="margin-left:10px">Delete</button>
    `;
    container.appendChild(div);
    updateWordPairDelete();
  };

  async function saveWordMatch() {
    const wmQuestionImageUrl = document.getElementById('wmQuestionImageUrl').value || null;
    const pairs = Array.from(document.querySelectorAll('.word-match-pair')).map(p => ({
      left: p.querySelector('.wm-left').value.trim(),
      right: p.querySelector('.wm-right').value.trim(),
      left_image_url: p.querySelector('.wm-left-image-url').value || null,
      right_image_url: p.querySelector('.wm-right-image-url').value || null
    }));
    
    // Validate: require text unless image is provided
    if (!pairs.length) {
      alert('Add at least one word pair'); return;
    }
    
    for (const p of pairs) {
      const hasLeftText = !!p.left;
      const hasLeftImage = !!p.left_image_url;
      const hasRightText = !!p.right;
      const hasRightImage = !!p.right_image_url;
      
      if (!hasLeftText && !hasLeftImage) {
        alert('Each pair must have left text or image'); return;
      }
      if (!hasRightText && !hasRightImage) {
        alert('Each pair must have right text or image'); return;
      }
    }

    const payload = {
      type: 'word_match',
      prompt_text: 'Match the following words:',
      prompt_image_url: wmQuestionImageUrl,
      word_pairs: pairs
    };
    const r = await fetch(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(payload)
    });
    if (r.status === 201) {
      resetWordMatchEditor();
      hideAllEditors();
      loadQuiz();
    } else {
      alert('Failed to save word match');
    }
  }
  
  document.getElementById('saveWordMatch').onclick = saveWordMatch;

  document.getElementById('cancelWordMatch').onclick = () => hideAllEditors();

  return { updateWordPairDelete, resetWordMatchEditor };
}

export async function updateWordMatch(questionId, token, quizId, resetWordMatchEditor, hideAllEditors, loadQuiz) {
  const wmQuestionImageUrl = document.getElementById('wmQuestionImageUrl').value || null;
  const pairs = Array.from(document.querySelectorAll('.word-match-pair')).map(p => ({
    left: p.querySelector('.wm-left').value.trim(),
    right: p.querySelector('.wm-right').value.trim(),
    left_image_url: p.querySelector('.wm-left-image-url').value || null,
    right_image_url: p.querySelector('.wm-right-image-url').value || null
  }));
  
  // Validate: require text unless image is provided
  if (!pairs.length) {
    alert('Add at least one word pair'); return;
  }
  
  for (const p of pairs) {
    const hasLeftText = !!p.left;
    const hasLeftImage = !!p.left_image_url;
    const hasRightText = !!p.right;
    const hasRightImage = !!p.right_image_url;
    
    if (!hasLeftText && !hasLeftImage) {
      alert('Each pair must have left text or image'); return;
    }
    if (!hasRightText && !hasRightImage) {
      alert('Each pair must have right text or image'); return;
    }
  }

  // Delete old question
  await fetch(`/quizzes/${quizId}/questions/${questionId}`, {
    method: 'DELETE',
    headers: {'Authorization': 'Bearer ' + token}
  });

  // Create new question with updated data
  const payload = {
    type: 'word_match',
    prompt_text: 'Match the following words:',
    prompt_image_url: wmQuestionImageUrl,
    word_pairs: pairs
  };
  const r = await fetch(`/quizzes/${quizId}/questions`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
    body: JSON.stringify(payload)
  });
  
  if (r.status === 201) {
    resetWordMatchEditor();
    hideAllEditors();
    loadQuiz();
  } else {
    alert('Failed to update word match');
  }
}
