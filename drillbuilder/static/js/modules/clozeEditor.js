// Cloze Editor functionality
let clozeWordData = {}; // Store word data including alternates

export function initClozeEditor(token, quizId, hideAllEditors, loadQuiz) {
  const saveClozeOriginal = async () => {
    const text = document.getElementById('clozeText').value.trim();
    const wordBank = document.getElementById('clozeWordBank').checked;
    const clozeQuestionImageUrl = document.getElementById('clozeQuestionImageUrl').value || null;
    
    const blanks = Object.values(clozeWordData).map(data => ({
      word: data.word,
      char_position: data.pos,
      alternates: data.alternates
    }));

    console.log('Cloze blanks:', blanks);
    
    if (!blanks.length) { alert('Select at least one word as blank'); return; }

    const payload = {
      type: 'cloze',
      prompt_text: text,
      prompt_image_url: clozeQuestionImageUrl,
      cloze_data: { 
        full_text: text, 
        blanks,
        word_bank: wordBank
      }
    };
    
    const r = await fetch(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(payload)
    });
    
    if (r.status === 201) {
      resetClozeEditor();
      hideAllEditors();
      loadQuiz();
    } else {
      alert('Failed to save cloze');
    }
  };

  function resetClozeEditor() {
    document.getElementById('clozeText').value = '';
    document.getElementById('clozeWordBank').checked = false;
    document.getElementById('clozeQuestionImageUrl').value = '';
    document.getElementById('clozeQuestionImagePreview').innerHTML = '';
    document.getElementById('clozeStep1').style.display = 'block';
    document.getElementById('clozeStep2').style.display = 'none';
    clozeWordData = {};
    
    // Clear any editing data
    delete window.editingClozeData;
    
    // Reset save button
    const clozeBtn = document.getElementById('saveCloze');
    clozeBtn.innerText = 'Save Cloze Question';
    clozeBtn.onclick = saveClozeOriginal;
  }

  function showAltInput(idx, span, wrapper) {
    // Remove any existing alt input
    const existing = wrapper.querySelector('.alt-input-container');
    if (existing) existing.remove();
    
    const altContainer = document.createElement('div');
    altContainer.className = 'alt-input-container';
    altContainer.style.cssText = 'position:absolute; top:100%; left:0; background:white; border:1px solid #ccc; padding:5px; z-index:20; box-shadow:0 2px 5px rgba(0,0,0,0.2); min-width:150px;';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Alternate answer';
    input.style.cssText = 'width:100%; padding:4px; margin-bottom:5px;';
    
    const submitBtn = document.createElement('button');
    submitBtn.innerText = 'Add';
    submitBtn.style.marginRight = '5px';
    submitBtn.onclick = (e) => {
      e.stopPropagation();
      const altText = input.value.trim();
      if (altText) {
        clozeWordData[idx].alternates.push(altText);
        updateWordDisplay(idx, span);
        altContainer.remove();
      }
    };
    
    const cancelBtn = document.createElement('button');
    cancelBtn.innerText = 'Cancel';
    cancelBtn.onclick = (e) => {
      e.stopPropagation();
      altContainer.remove();
    };
    
    altContainer.appendChild(input);
    altContainer.appendChild(submitBtn);
    altContainer.appendChild(cancelBtn);
    wrapper.appendChild(altContainer);
    input.focus();
  }

  function updateWordDisplay(idx, span) {
    if (clozeWordData[idx]) {
      const data = clozeWordData[idx];
      const allWords = [data.word, ...data.alternates];
      span.innerText = allWords.join('/');
    }
  }

  // Cloze Next button
  document.getElementById('clozeNext').onclick = () => {
    const text = document.getElementById('clozeText').value.trim();
    if (!text) { alert('Enter text first'); return; }
    document.getElementById('clozeStep1').style.display = 'none';
    document.getElementById('clozeStep2').style.display = 'block';
    
    clozeWordData = {}; // Reset word data
    const words = text.split(/\s+/);
    const container = document.getElementById('clozeWordSelect');
    container.innerHTML = '';
    let charPos = 0;
    
    // Get existing blanks if we're editing
    const existingBlanks = window.editingClozeData?.existingBlanks || [];
    let removedCount = 0;
    
    words.forEach((word, idx) => {
      const wrapper = document.createElement('span');
      wrapper.style.position = 'relative';
      wrapper.style.display = 'inline-block';
      wrapper.style.marginRight = '5px';
      
      const span = document.createElement('span');
      span.innerText = word;
      span.style.cursor = 'pointer';
      span.dataset.word = word;
      const wordCharPos = charPos;
      span.dataset.pos = wordCharPos;
      console.log(`Setting position to ${wordCharPos} for word "${word}" at index ${idx}`);
      span.dataset.idx = idx;
      span.className = 'cloze-word';
      
      // Check if this word was previously a blank at this exact position
      const existingBlank = existingBlanks.find(b => b.char_position === wordCharPos && b.word === word);
      
      if (existingBlank) {
        // Restore the blank with its data
        span.classList.add('selected');
        span.style.background = 'yellow';
        clozeWordData[idx] = { 
          word: existingBlank.word, 
          pos: wordCharPos, 
          alternates: [...existingBlank.alternates] 
        };
        
        // Update display with alternates
        if (existingBlank.alternates.length > 0) {
          span.innerText = [existingBlank.word, ...existingBlank.alternates].join('/');
        }
        
        // Add "alt" button
        const altBtn = document.createElement('span');
        altBtn.className = 'alt-btn';
        altBtn.innerText = 'alt';
        altBtn.style.cssText = 'position:absolute; top:-20px; right:-5px; background:black; color:white; padding:2px 4px; font-size:10px; cursor:pointer; border-radius:3px; z-index:10; display:none;';
        altBtn.onclick = (e) => {
          e.stopPropagation();
          showAltInput(idx, span, wrapper);
        };
        wrapper.appendChild(altBtn);
        
        wrapper.onmouseenter = () => {
          const btn = wrapper.querySelector('.alt-btn');
          if (btn) btn.style.display = 'block';
        };
        wrapper.onmouseleave = () => {
          const btn = wrapper.querySelector('.alt-btn');
          if (btn) btn.style.display = 'none';
        };
      }
      
      span.onclick = () => {
        const isSelected = span.classList.contains('selected');
        span.classList.toggle('selected');
        
        if (!isSelected) {
          // Selecting the word
          span.style.background = 'yellow';
          clozeWordData[idx] = { word, pos: wordCharPos, alternates: [] };

          // Add "alt" button (hidden by default, shown on hover)
          const altBtn = document.createElement('span');
          altBtn.className = 'alt-btn';
          altBtn.innerText = 'alt';
          altBtn.style.cssText = 'position:absolute; top:-20px; right:-5px; background:black; color:white; padding:2px 4px; font-size:10px; cursor:pointer; border-radius:3px; z-index:10; display:none;';
          altBtn.onclick = (e) => {
            e.stopPropagation();
            showAltInput(idx, span, wrapper);
          };
          wrapper.appendChild(altBtn);
          
          // Show/hide alt button on hover
          wrapper.onmouseenter = () => {
            const btn = wrapper.querySelector('.alt-btn');
            if (btn) btn.style.display = 'block';
          };
          wrapper.onmouseleave = () => {
            const btn = wrapper.querySelector('.alt-btn');
            if (btn) btn.style.display = 'none';
          };
        } else {
          // Deselecting the word
          span.style.background = '';
          delete clozeWordData[idx];
          // Remove alt button and any alt input
          const altBtn = wrapper.querySelector('.alt-btn');
          if (altBtn) altBtn.remove();
          const altInput = wrapper.querySelector('.alt-input-container');
          if (altInput) altInput.remove();
        }
        
        updateWordDisplay(idx, span);
      };
      
      wrapper.appendChild(span);
      container.appendChild(wrapper);
      container.appendChild(document.createTextNode(' '));
      charPos += word.length + 1;
    });
    
    // Count how many blanks were removed
    removedCount = existingBlanks.length - Object.keys(clozeWordData).length;
    if (removedCount > 0) {
      console.log(`Removed ${removedCount} blank(s) that no longer match original position/word`);
    }
    
    // Clear the editing data
    delete window.editingClozeData;
  };

  document.getElementById('cancelClozeStep1').onclick = () => {
    resetClozeEditor();
    hideAllEditors();
  };

  document.getElementById('saveCloze').onclick = saveClozeOriginal;

  document.getElementById('cancelCloze').onclick = () => {
    resetClozeEditor();
    hideAllEditors();
  };

  return { resetClozeEditor, saveClozeOriginal, clozeWordData: () => clozeWordData };
}

export async function updateCloze(questionId, token, quizId, resetClozeEditor, hideAllEditors, loadQuiz, getClozeWordData) {
  const text = document.getElementById('clozeText').value.trim();
  const wordBank = document.getElementById('clozeWordBank').checked;
  const clozeQuestionImageUrl = document.getElementById('clozeQuestionImageUrl').value || null;
  
  const clozeWordData = getClozeWordData();
  const blanks = Object.values(clozeWordData).map(data => ({
    word: data.word,
    char_position: data.pos,
    alternates: data.alternates
  }));

  if (!blanks.length) { alert('Select at least one word as blank'); return; }

  // Delete old question and create new one
  const delR = await fetch(`/quizzes/${quizId}/questions/${questionId}`, {
    method: 'DELETE',
    headers: {'Authorization': 'Bearer ' + token}
  });
  
  if (delR.ok) {
    const payload = {
      type: 'cloze',
      prompt_text: text,
      prompt_image_url: clozeQuestionImageUrl,
      cloze_data: { 
        full_text: text, 
        blanks,
        word_bank: wordBank
      }
    };
    
    const r = await fetch(`/quizzes/${quizId}/questions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(payload)
    });
    
    if (r.status === 201) {
      resetClozeEditor();
      hideAllEditors();
      loadQuiz();
    } else {
      alert('Failed to update cloze');
    }
  } else {
    alert('Failed to delete old question');
  }
}
