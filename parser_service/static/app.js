(() => {
  const form = document.getElementById('uploadForm');
  const resumesInput = document.getElementById('resumes');
  const jdInput = document.getElementById('jd');
  const resultsEl = document.getElementById('results');
  const submitBtn = document.getElementById('submitBtn');
  const clearBtn = document.getElementById('clearBtn');
  const progress = document.getElementById('progress');

  const API_URL = '/parse_resume';

  // Handle form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (resumesInput.files.length === 0) {
      alert('Please select at least one resume file.');
      return;
    }

    submitBtn.disabled = true;
    progress.style.display = 'block';
    progress.value = 20;

    const formData = new FormData();
    for (let i = 0; i < resumesInput.files.length; i++) {
      formData.append('resumes', resumesInput.files[i]);
    }
    formData.append('job_description', jdInput.value);

    try {
      progress.value = 40;
      const res = await fetch(API_URL, { method: 'POST', body: formData });
      progress.value = 70;
      const data = await res.json();
      progress.value = 100;

      if (data.leaderboard) renderResults(data.leaderboard);
    } catch (err) {
      alert('Error parsing resumes: ' + err.message);
    } finally {
      submitBtn.disabled = false;
      progress.style.display = 'none';
      progress.value = 0;
    }
  });

  // Render results dynamically
  function renderResults(list) {
    resultsEl.innerHTML = '';
    list.forEach((item, i) => {
      const div = document.createElement('div');
      div.className = 'item';
      div.innerHTML = `
        <div class="meta">
          <h3>${i + 1}. ${item.name || 'Unknown Candidate'}</h3>
          <div class="tags">${item.skills.join(', ') || 'No skills found'}</div>
        </div>
        <div class="score">${item.final_score}%</div>
      `;
      resultsEl.appendChild(div);
    });
  }

  // Clear form
  clearBtn.addEventListener('click', () => {
    resumesInput.value = '';
    jdInput.value = '';
    resultsEl.innerHTML = '<p class="muted">No results yet. Upload resumes and click "Parse & Rank".</p>';
  });
})();
