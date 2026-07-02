/**
 * Dynamic Update System
 * Allows real-time content modifications without file imports
 */

class DynamicUpdater extends HTMLElement {
    constructor() {
        super();
        this.apiEndpoint = this.getAttribute('api-endpoint');
        this.updateInterval = parseInt(this.getAttribute('update-interval')) || 5000;
    }
    
    connectedCallback() {
        console.log('Dynamic Updater System Initialized');
        this.initializeUpdateSystem();
    }
    
    initializeUpdateSystem() {
        // Listen for custom update events
        document.addEventListener('requestUpdate', (e) => this.handleUpdateRequest(e.detail));
        document.addEventListener('contentModified', (e) => this.handleContentModification(e.detail));
        
        // Expose global API for external calls
        window.SmartContentAPI = {
            rewriteSection: (sectionId, style) => this.rewriteSection(sectionId, style),
            addImages: (sections, count) => this.addImagesToSections(sections, count),
            changeStyle: (projectId, style) => this.changeDocumentStyle(projectId, style),
            expandSection: (sectionId, words) => this.expandSection(sectionId, words),
            applyCustomPrompt: (sectionId, prompt) => this.applyCustomPrompt(sectionId, prompt),
            getStatus: (projectId) => this.getProjectStatus(projectId),
            updateContent: (sectionId, newContent) => this.updateContent(sectionId, newContent)
        };
    }
    
    async handleUpdateRequest(detail) {
        const { type, data } = detail;
        
        try {
            const response = await this.sendUpdate(type, data);
            
            if (response.success) {
                this.applyChanges(response.changes);
                this.dispatchUpdateEvent('updateCompleted', response);
            } else {
                console.error('Update failed:', response.error);
                this.dispatchUpdateEvent('updateFailed', response);
            }
        } catch (error) {
            console.error('Update error:', error);
            this.dispatchUpdateEvent('updateError', { error: error.message });
        }
    }
    
    async sendUpdate(type, data) {
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                type: type,
                data: data
            })
        });
        
        return await response.json();
    }
    
    applyChanges(changes) {
        if (changes.new_content) {
            this.updateContentDisplay(changes.new_content);
        }
        
        if (changes.images) {
            this.insertImages(changes.images);
        }
        
        if (changes.expanded_content) {
            this.appendContent(changes.expanded_content);
        }
        
        if (changes.modified_content) {
            this.replaceContent(changes.modified_content);
        }
    }
    
    // Public API methods
    async rewriteSection(sectionId, style = 'academic') {
        return await this.handleUpdateRequest({
            type: 'rewrite_section',
            data: { section_id: sectionId, style: style }
        });
    }
    
    async addImagesToSections(sections, count = 2) {
        return await this.handleUpdateRequest({
            type: 'add_images',
            data: { sections: sections, image_count: count }
        });
    }
    
    async changeDocumentStyle(projectId, style) {
        return await this.handleUpdateRequest({
            type: 'change_style',
            data: { project_id: projectId, style: style }
        });
    }
    
    async expandSection(sectionId, additionalWords = 500) {
        return await this.handleUpdateRequest({
            type: 'expand_section',
            data: { section_id: sectionId, additional_words: additionalWords }
        });
    }
    
    async applyCustomPrompt(sectionId, prompt) {
        return await this.handleUpdateRequest({
            type: 'custom_prompt',
            data: { section_id: sectionId, prompt: prompt }
        });
    }
    
    // DOM manipulation methods
    updateContentDisplay(content) {
        const editorArea = document.querySelector('#contentEditor');
        if (editorArea) {
            editorArea.innerHTML = content;
        }
    }
    
    insertImages(images) {
        images.forEach(img => {
            const imgElement = document.createElement('img');
            imgElement.src = img.url;
            imgElement.alt = img.alt;
            imgElement.className = 'content-image';
            
            const container = document.querySelector(`#section-${img.sectionId}`);
            if (container) {
                container.appendChild(imgElement);
            }
        });
    }
    
    appendContent(content) {
        const targetSection = document.querySelector('.active-section');
        if (targetSection) {
            targetSection.innerHTML += content;
        }
    }
    
    replaceContent(content) {
        const targetSection = document.querySelector('.active-section');
        if (targetSection) {
            targetSection.innerHTML = content;
        }
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    dispatchUpdateEvent(name, detail) {
        document.dispatchEvent(new CustomEvent(name, { detail: detail }));
    }
}

// Register the custom element
customElements.define('dynamic-updater', DynamicUpdater);
