// Upload functionality
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const useLocalFileBtn = document.getElementById('useLocalFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const statusMessage = document.getElementById('statusMessage');
    const optimizeSection = document.getElementById('optimizeSection');
    const optimizeBtn = document.getElementById('optimizeBtn');
    const loadingSection = document.getElementById('loadingSection');

    // File upload form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        showLoading(true);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            handleUploadResponse(data);
        })
        .catch(error => {
            showLoading(false);
            showStatus('Error: ' + error.message, 'danger');
        });
    });

    // Use local file button
    useLocalFileBtn.addEventListener('click', function() {
        showLoading(true);
        
        fetch('/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            handleUploadResponse(data);
        })
        .catch(error => {
            showLoading(false);
            showStatus('Error: ' + error.message, 'danger');
        });
    });

    // Optimize routes button
    optimizeBtn.addEventListener('click', function() {
        const truckCount = document.getElementById('truckCount').value;
        showOptimizeLoading(true);
        
        fetch('/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                num_trucks: parseInt(truckCount)
            })
        })
        .then(response => response.json())
        .then(data => {
            showOptimizeLoading(false);
            
            if (data.success) {
                // Redirect to results page
                window.location.href = '/results';
            } else {
                showStatus('Error: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            showOptimizeLoading(false);
            showStatus('Error: ' + error.message, 'danger');
        });
    });

    // Handle upload response
    function handleUploadResponse(data) {
        if (data.success) {
            showStatus(data.message, 'success');
            optimizeSection.style.display = 'block';
            
            // Scroll to optimize section
            optimizeSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            showStatus('Error: ' + data.error, 'danger');
            optimizeSection.style.display = 'none';
        }
    }

    // Show status message
    function showStatus(message, type) {
        statusMessage.className = `alert alert-${type}`;
        statusMessage.textContent = message;
        uploadStatus.style.display = 'block';
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                uploadStatus.style.display = 'none';
            }, 5000);
        }
    }

    // Show/hide loading for upload
    function showLoading(show) {
        const buttons = uploadForm.querySelectorAll('button');
        
        buttons.forEach(btn => {
            btn.disabled = show;
            if (show) {
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Procesando...';
            } else {
                // Restore original text
                if (btn.id === 'useLocalFile') {
                    btn.innerHTML = '<i class="fas fa-file"></i> Usar Archivo Local';
                } else {
                    btn.innerHTML = '<i class="fas fa-upload"></i> Subir Archivo';
                }
            }
        });
    }

    // Show/hide loading for optimization
    function showOptimizeLoading(show) {
        if (show) {
            optimizeSection.style.display = 'none';
            loadingSection.style.display = 'block';
            
            // Simulate progress updates
            simulateProgress();
        } else {
            loadingSection.style.display = 'none';
            optimizeSection.style.display = 'block';
        }
    }

    // Simulate progress for user feedback
    function simulateProgress() {
        const steps = [
            'Geocodificando direcciones...',
            'Agrupando por capacidad...',
            'Optimizando rutas...',
            'Calculando distancias...',
            'Generando mapa...'
        ];
        
        let currentStep = 0;
        const progressText = loadingSection.querySelector('p');
        
        const updateStep = () => {
            if (currentStep < steps.length) {
                progressText.textContent = steps[currentStep];
                currentStep++;
                setTimeout(updateStep, 2000);
            }
        };
        
        updateStep();
    }

    // Drag and drop functionality
    const uploadZone = document.querySelector('.card-body');
    
    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadZone.classList.add('upload-zone', 'dragover');
    });
    
    uploadZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const fileInput = document.getElementById('csvFile');
            fileInput.files = files;
            
            // Trigger form submission
            uploadForm.dispatchEvent(new Event('submit'));
        }
    });
});