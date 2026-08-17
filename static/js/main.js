/**
 * Student Management System — Main Client-Side Scripts
 */

document.addEventListener('DOMContentLoaded', function() {
  // 1. Auto-dismiss flash alerts / toasts after 5s
  document.querySelectorAll('.toast').forEach(toast => {
    setTimeout(() => {
      toast.classList.add('hiding');
      setTimeout(() => toast.remove(), 260);
    }, 5000);
  });

  // 2. Initialize date inputs with today's date if empty
  document.querySelectorAll('input[type="date"]').forEach(input => {
    if (!input.value) {
      input.value = new Date().toISOString().split('T')[0];
    }
  });

  // 3. Photo preview
  const photoInput = document.querySelector('input[type="file"][name="photo"]');
  if (photoInput) {
    photoInput.addEventListener('change', function() {
      const file = this.files[0];
      if (file) {
        if (!file.type.startsWith('image/')) {
          alert('Please select a valid image file.');
          this.value = '';
          return;
        }
        if (file.size > 5 * 1024 * 1024) {
          alert('Image size exceeds 5MB limit.');
          this.value = '';
          return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
          let preview = document.querySelector('.photo-preview-img');
          if (!preview) {
            preview = document.createElement('img');
            preview.className = 'photo-preview-img mt-2';
            preview.style.width = '80px';
            preview.style.height = '80px';
            preview.style.borderRadius = '50%';
            preview.style.objectFit = 'cover';
            photoInput.parentElement.appendChild(preview);
          }
          preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // 4. CSV file upload validation
  const csvInput = document.querySelector('input[type="file"][name="csv_file"]');
  if (csvInput) {
    csvInput.addEventListener('change', function() {
      const file = this.files[0];
      if (file) {
        if (!file.name.toLowerCase().endsWith('.csv')) {
          alert('Please select a .csv file.');
          this.value = '';
          return;
        }
        if (file.size > 10 * 1024 * 1024) {
          alert('File size exceeds 10MB limit.');
          this.value = '';
        }
      }
    });
  }

  // 5. Prevent double form submissions on button click
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        // Only disable if form is valid
        if (form.checkValidity()) {
          setTimeout(() => {
            submitBtn.disabled = true;
          }, 0);
        }
      }
    });
  });
});
