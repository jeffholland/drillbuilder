// Image upload functionality
export function triggerImageUpload(inputIdOrElement) {
  const input = typeof inputIdOrElement === 'string' ? 
    document.getElementById(inputIdOrElement) : inputIdOrElement;
  if (input) input.click();
}

export async function handleImageUpload(fileInput, previewId, urlInputId, token) {
  const file = fileInput.files[0];
  if (!file) return;
  
  // Validate file type
  if (!file.name.match(/\.(jpg|jpeg)$/i)) {
    alert('Only .jpg and .jpeg files are allowed');
    fileInput.value = '';
    return;
  }
  
  // Upload file
  const formData = new FormData();
  formData.append('image', file);
  
  try {
    const response = await fetch('/images/upload', {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + token},
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      document.getElementById(urlInputId).value = data.image_url;
      
      // Show preview
      const preview = document.getElementById(previewId);
      preview.innerHTML = `<img src="${data.image_url}" style="max-width:100px;max-height:100px;border:1px solid #ddd;border-radius:4px;" /> <button type="button" onclick="window.imageUpload.removeImage('${urlInputId}', '${previewId}')" style="font-size:11px;padding:2px 6px;">✕</button>`;
    } else {
      alert('Failed to upload image');
      fileInput.value = '';
    }
  } catch (error) {
    alert('Error uploading image: ' + error.message);
    fileInput.value = '';
  }
}

export async function handleChoiceImageUpload(fileInput, token) {
  const file = fileInput.files[0];
  if (!file) return;
  
  if (!file.name.match(/\.(jpg|jpeg)$/i)) {
    alert('Only .jpg and .jpeg files are allowed');
    fileInput.value = '';
    return;
  }
  
  const formData = new FormData();
  formData.append('image', file);
  
  try {
    const response = await fetch('/images/upload', {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + token},
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      const choice = fileInput.closest('.mcq-choice');
      choice.querySelector('.choice-image-url').value = data.image_url;
      
      const preview = choice.querySelector('.choice-image-preview');
      preview.innerHTML = `<img src="${data.image_url}" style="max-width:50px;max-height:50px;border:1px solid #ddd;border-radius:3px;vertical-align:middle;" />`;
    } else {
      alert('Failed to upload image');
      fileInput.value = '';
    }
  } catch (error) {
    alert('Error uploading image: ' + error.message);
    fileInput.value = '';
  }
}

export async function handleWMImageUpload(fileInput, side, token) {
  const file = fileInput.files[0];
  if (!file) return;
  
  if (!file.name.match(/\.(jpg|jpeg)$/i)) {
    alert('Only .jpg and .jpeg files are allowed');
    fileInput.value = '';
    return;
  }
  
  const formData = new FormData();
  formData.append('image', file);
  
  try {
    const response = await fetch('/images/upload', {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + token},
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      const pair = fileInput.closest('.word-match-pair');
      pair.querySelector(`.wm-${side}-image-url`).value = data.image_url;
      
      const preview = pair.querySelector(`.wm-${side}-preview`);
      preview.innerHTML = `<img src="${data.image_url}" style="max-width:50px;max-height:50px;border:1px solid #ddd;border-radius:3px;vertical-align:middle;" />`;
    } else {
      alert('Failed to upload image');
      fileInput.value = '';
    }
  } catch (error) {
    alert('Error uploading image: ' + error.message);
    fileInput.value = '';
  }
}

export function triggerWMImageUpload(button, side) {
  const pair = button.closest('.word-match-pair');
  const input = pair.querySelector(`.wm-${side}-image-input`);
  if (input) input.click();
}

export function removeImage(urlInputId, previewId) {
  document.getElementById(urlInputId).value = '';
  document.getElementById(previewId).innerHTML = '';
}
