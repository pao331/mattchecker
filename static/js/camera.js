document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');
    const resetBtn = document.getElementById('resetBtn');
    const captureResult = document.getElementById('captureResult');
    const capturedImage = document.getElementById('capturedImage');
    const imageData = document.getElementById('imageData');
    const captureForm = document.getElementById('captureForm');
    const submitBtn = document.getElementById('submitBtn');
    const processingIndicator = document.getElementById('processingIndicator');
    
    // Variables
    let stream = null;
    
    // Initialize camera on page load
    initCamera();
    
    // Event listeners
    captureBtn.addEventListener('click', captureImage);
    resetBtn.addEventListener('click', resetCamera);
    
    // Override form submission to use fetch API for larger images
    if (captureForm) {
        captureForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show processing indicator
            if (processingIndicator) {
                processingIndicator.classList.remove('d-none');
            }
            if (submitBtn) {
                submitBtn.disabled = true;
            }
            
            // Get the template selection
            const templateSelect = document.getElementById('template');
            const selectedTemplate = templateSelect ? templateSelect.value : 'standard_20';
            
            // Get the image data
            const dataURL = imageData.value;
            
            // Submit using fetch API instead of form post
            fetch('/process_camera_image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_data: dataURL,
                    template: selectedTemplate
                })
            })
            .then(response => {
                if (response.redirected) {
                    // If we got redirected, follow the redirect
                    window.location.href = response.url;
                } else {
                    return response.json().then(data => {
                        // Handle JSON response
                        if (data.error) {
                            // Show error message in a more user-friendly way
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'alert alert-danger mt-3';
                            errorDiv.innerHTML = `<strong>Error:</strong> ${data.error} <br>
                            <small>Please make sure you're capturing a valid exam sheet with clear student information.</small>`;
                            
                            // Insert the error message before the form
                            captureForm.parentNode.insertBefore(errorDiv, captureForm);
                            
                            // Hide processing indicator and re-enable submit button
                            if (processingIndicator) {
                                processingIndicator.classList.add('d-none');
                            }
                            if (submitBtn) {
                                submitBtn.disabled = false;
                            }
                            
                            // Auto-scroll to the error message
                            errorDiv.scrollIntoView({ behavior: 'smooth' });
                            
                            // Set a timeout to remove the error message after 10 seconds
                            setTimeout(() => {
                                errorDiv.classList.add('fade');
                                setTimeout(() => {
                                    if (errorDiv.parentNode) {
                                        errorDiv.parentNode.removeChild(errorDiv);
                                    }
                                }, 500);
                            }, 10000);
                        } else {
                            // If no redirect but successful, go to results page
                            window.location.href = '/result/' + data.scan_id;
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred during submission. Please try again.');
                
                // Hide processing indicator and re-enable submit button
                if (processingIndicator) {
                    processingIndicator.classList.add('d-none');
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
            });
        });
    }
    
    // Functions
    function initCamera() {
        // Check if the browser supports getUserMedia
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Your browser does not support camera access. Please try another browser.');
            return;
        }
        
        // Camera constraints - prefer back camera if available (better for document scanning)
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };
        
        // Get camera stream
        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(mediaStream) {
                stream = mediaStream;
                video.srcObject = mediaStream;
                video.play();
                
                // Show the capture button
                captureBtn.classList.remove('d-none');
            })
            .catch(function(error) {
                console.error('Error accessing the camera:', error);
                alert('Error accessing the camera: ' + error.message);
            });
    }
    
    function captureImage() {
        // Get canvas context
        const context = canvas.getContext('2d');
        
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw the current video frame on the canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to an image
        const dataURL = canvas.toDataURL('image/png');
        capturedImage.src = dataURL;
        imageData.value = dataURL;
        
        // Show the captured image and form
        captureResult.classList.remove('d-none');
        
        // Hide capture button and show reset button
        captureBtn.classList.add('d-none');
        resetBtn.classList.remove('d-none');
        
        // Stop the camera stream
        stopStream();
    }
    
    function resetCamera() {
        // Hide the captured image and results
        captureResult.classList.add('d-none');
        
        // Show capture button and hide reset button
        captureBtn.classList.remove('d-none');
        resetBtn.classList.add('d-none');
        
        // Restart the camera
        initCamera();
    }
    
    function stopStream() {
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
            });
        }
    }
    
    // Clean up when leaving the page
    window.addEventListener('beforeunload', function() {
        stopStream();
    });
});
