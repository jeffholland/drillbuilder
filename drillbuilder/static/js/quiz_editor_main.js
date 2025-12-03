// Main quiz editor script
import * as imageUpload from './modules/imageUpload.js';
import * as mcqEditor from './modules/mcqEditor.js';
import * as clozeEditor from './modules/clozeEditor.js';
import * as wordMatchEditor from './modules/wordMatchEditor.js';
import * as quizManager from './modules/quizManager.js';

// Global state
const token = localStorage.getItem('access_token');
if (!token) { window.location = '/register'; }

const quizId = new URLSearchParams(window.location.search).get('id');
if (!quizId) { window.location = '/dashboard'; }

let allQuestions = [];

// Expose image upload functions to window for inline handlers
window.imageUpload = imageUpload;
window.handleChoiceImageUpload = (fileInput) => imageUpload.handleChoiceImageUpload(fileInput, token);
window.handleWMImageUpload = (fileInput, side) => imageUpload.handleWMImageUpload(fileInput, side, token);

// Load quiz wrapper
const loadQuizWrapper = () => quizManager.loadQuiz(quizId, token, (questions) => 
  quizManager.renderQuestions(questions, (q) => { allQuestions = q; })
);

// Initialize editors
const mcqEditorState = mcqEditor.initMCQEditor(token, quizId, quizManager.hideAllEditors, loadQuizWrapper);
const clozeEditorState = clozeEditor.initClozeEditor(token, quizId, quizManager.hideAllEditors, loadQuizWrapper);
const wordMatchEditorState = wordMatchEditor.initWordMatchEditor(token, quizId, quizManager.hideAllEditors, loadQuizWrapper);

// Edit question function
function editQuestion(questionId) {
  const question = allQuestions.find(q => q.id === questionId);
  if (!question) return;
  
  quizManager.hideAllEditors();
  
  if (question.type === 'multiple_choice') {
    // Load MCQ into editor
    document.getElementById('mcqPrompt').value = question.prompt_text;
    document.getElementById('mcqQuestionImageUrl').value = question.prompt_image_url || '';
    if (question.prompt_image_url) {
      document.getElementById('mcqQuestionImagePreview').innerHTML = `<img src="${question.prompt_image_url}" style="max-width:100px;max-height:100px;border:1px solid #ddd;border-radius:4px;" /> <button type="button" onclick="window.imageUpload.removeImage('mcqQuestionImageUrl', 'mcqQuestionImagePreview')" style="font-size:11px;padding:2px 6px;">✕</button>`;
    }
    
    const container = document.getElementById('mcqChoices');
    container.innerHTML = '';
    question.options.forEach(opt => {
      const div = document.createElement('div');
      div.className = 'mcq-choice';
      div.innerHTML = `
        <input type="text" placeholder="Choice" class="mcq-text" value="${opt.text}" />
        <label><input type="checkbox" class="mcq-correct" ${opt.is_correct ? 'checked' : ''} /> Correct</label>
        <button type="button" class="choice-image-btn" onclick="window.imageUpload.triggerImageUpload(this.parentElement.querySelector('.choice-image-input'))" style="font-size:11px;padding:2px 6px;margin-left:8px;">📷</button>
        <input type="file" class="choice-image-input" accept=".jpg,.jpeg" style="display:none" onchange="window.handleChoiceImageUpload(this)" />
        <input type="hidden" class="choice-image-url" value="${opt.image_url || ''}" />
        <div class="choice-image-preview" style="display:inline-block;margin-left:5px;">${opt.image_url ? `<img src="${opt.image_url}" style="max-width:50px;max-height:50px;border:1px solid #ddd;border-radius:3px;vertical-align:middle;" />` : ''}</div>
        <button class="delete-choice" style="margin-left:10px">Delete</button>
      `;
      container.appendChild(div);
    });
    
    mcqEditorState.updateDeleteButtons();
    document.getElementById('mcqEditor').style.display = 'block';
    
    // Change save button to update
    const saveBtn = document.getElementById('saveMcq');
    saveBtn.innerText = 'Update MCQ';
    saveBtn.onclick = () => mcqEditor.updateMcq(questionId, token, quizId, mcqEditorState.resetMcqEditor, quizManager.hideAllEditors, loadQuizWrapper);
    
  } else if (question.type === 'cloze') {
    // Load Cloze into editor - start at step 1 to allow text editing
    const clozeData = question.cloze_question;
    if (!clozeData) {
      alert('Invalid cloze question data');
      return;
    }
    
    document.getElementById('clozeText').value = clozeData.full_text;
    document.getElementById('clozeQuestionImageUrl').value = question.prompt_image_url || '';
    document.getElementById('clozeWordBank').checked = clozeData.word_bank || false;
    
    if (question.prompt_image_url) {
      document.getElementById('clozeQuestionImagePreview').innerHTML = `<img src="${question.prompt_image_url}" style="max-width:100px;max-height:100px;border:1px solid #ddd;border-radius:4px;" /> <button type="button" onclick="window.imageUpload.removeImage('clozeQuestionImageUrl', 'clozeQuestionImagePreview')" style="font-size:11px;padding:2px 6px;">✕</button>`;
    }
    
    // Store existing blanks data for restoration in step 2
    const existingBlanks = (clozeData.cloze_words || clozeData.blanks || []).map(b => ({
      word: b.correct_answer || b.word,
      char_position: b.char_position,
      alternates: b.alternate_answers || b.alternates || []
    }));
    
    // Store in a temporary variable accessible to the Next button
    window.editingClozeData = { existingBlanks };
    
    // Show step 1
    document.getElementById('clozeStep1').style.display = 'block';
    document.getElementById('clozeStep2').style.display = 'none';
    document.getElementById('clozeEditor').style.display = 'block';
    
    // Change save button to update (in case they go to step 2)
    const clozeBtn = document.getElementById('saveCloze');
    clozeBtn.innerText = 'Update Cloze';
    clozeBtn.onclick = () => clozeEditor.updateCloze(questionId, token, quizId, clozeEditorState.resetClozeEditor, quizManager.hideAllEditors, loadQuizWrapper, clozeEditorState.clozeWordData);
    
  } else if (question.type === 'word_match') {
    alert('Editing word match questions is not yet implemented. Please delete and recreate.');
  }
}

// Delete question function
function deleteQuestion(questionId) {
  quizManager.deleteQuestion(questionId, quizId, token, loadQuizWrapper);
}

// Add question button
document.getElementById('addQuestionBtn').onclick = () => {
  const type = document.getElementById('questionType').value;
  quizManager.hideAllEditors();
  if (type === 'mcq') {
    document.getElementById('mcqEditor').style.display = 'block';
    mcqEditorState.updateDeleteButtons();
  } else if (type === 'cloze') {
    document.getElementById('clozeEditor').style.display = 'block';
  } else if (type === 'word_match') {
    document.getElementById('wordMatchEditor').style.display = 'block';
  }
};

// Expose functions to window for inline handlers
window.editQuestion = editQuestion;
window.deleteQuestion = deleteQuestion;

// Load quiz on page load
document.addEventListener('DOMContentLoaded', () => {
  loadQuizWrapper();
});
