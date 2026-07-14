# Request the SanPy Desktop App

Please fill out the form below to request the SanPy desktop app. We will email you with a download link.

As always, contact Robert Cudmore (rober.cudmore@gmail.com) with any questions. We are always looking for collaborators and users!

<style>
.sp-form {
    max-width: 700px;
    margin-top: 0.6rem;
}

.sp-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem 0.75rem;
}

.sp-form .sp-field {
    margin: 0 !important;
    padding: 0 !important;
}

.sp-form .sp-field-full {
    grid-column: 1 / -1;
}

.sp-form .sp-field label {
    display: block;
    margin: 0 0 0.1rem 0 !important;
    padding: 0 !important;
    font-weight: 600;
    line-height: 1.15;
}

.sp-form .sp-input,
.sp-form .sp-textarea {
    display: block;
    width: 100%;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0.32rem 0.5rem !important;
    border: 1px solid #aaa;
    border-radius: 4px;
    box-sizing: border-box;
    font: inherit;
    line-height: 1.2;
}

.sp-form .sp-textarea {
    resize: vertical;
}

.sp-form .sp-button {
    margin-top: 0.55rem !important;
    padding: 0.45rem 1rem !important;
    border: none;
    border-radius: 4px;
    background: #1976d2;
    color: white;
    font: inherit;
    font-weight: 600;
    line-height: 1.2;
    cursor: pointer;
}

@media (max-width: 600px) {
    .sp-form-grid {
        grid-template-columns: 1fr;
    }

    .sp-form .sp-field-full {
        grid-column: auto;
    }
}
</style>

<form class="sp-form" action="https://formspree.io/f/mwpqrayn" method="POST">

<div class="sp-form-grid">

<div class="sp-field">
<label for="name">Name</label>
<input class="sp-input" type="text" id="name" name="name" placeholder="Jane Smith">
</div>

<div class="sp-field">
<label for="institution">University / Institution</label>
<input class="sp-input" type="text" id="institution" name="institution" placeholder="University of California">
</div>

<div class="sp-field">
<label for="lab">Lab</label>
<input class="sp-input" type="text" id="lab" name="lab" placeholder="Smith Lab">
</div>

<div class="sp-field">
<label for="email">Email <span style="color:#c00">*</span></label>
<input class="sp-input" type="email" id="email" name="email" required placeholder="name@example.edu">
</div>

<div class="sp-field sp-field-full">
<label for="platform">Desktop Version (macOS or Windows)</label>
<input class="sp-input" type="text" id="platform" name="platform" placeholder="macOS or Windows">
</div>

<div class="sp-field sp-field-full">
<label for="comments">Comments</label>
<textarea class="sp-input sp-textarea" id="comments" name="comments" rows="2" placeholder="Tell us anything you'd like us to know..."></textarea>
</div>

</div>

<button class="sp-button" type="submit">Submit Request</button>

</form>
