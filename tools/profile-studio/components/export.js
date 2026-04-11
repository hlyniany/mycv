var exportComponent = {
	template: '#export-template',

	

	mounted: function()
	{
		this.json = JSON.stringify(this.$root.sections, null, 4);
	},



	destroyed: function()
	{
		
	},


	
	data: function()
	{
		return {
			json: "",
			saving: false,
			saveMessage: "",
			saveStatus: ""
		};
	},

	

	methods: {
		downloadJson: function()
		{
			// Create a blob from the JSON string
			const blob = new Blob([this.json], { type: 'application/json' });
			
			// Create a temporary download link
			const url = window.URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			
			// Set filename with current date
			const date = new Date().toISOString().split('T')[0];
			link.download = `cv.resume.${date}.json`;
			
			// Trigger download
			document.body.appendChild(link);
			link.click();
			
			// Clean up
			document.body.removeChild(link);
			window.URL.revokeObjectURL(url);
		},

		saveToProject: async function()
		{
			try {
				this.saving = true;
				this.saveMessage = '';
				
				// Parse JSON to ensure it's valid
				const data = JSON.parse(this.json);
				
				// Send to backend
				const response = await fetch('/api/save-cv', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify(data)
				});
				
				const result = await response.json();
				
				if (response.ok) {
					this.saveMessage = '✓ ' + result.message + ' to ' + result.file;
					this.saveStatus = 'success';
				} else {
					this.saveMessage = '✗ Error: ' + (result.error || 'Unknown error');
					this.saveStatus = 'error';
				}
			} catch (error) {
				this.saveMessage = '✗ Error: ' + error.message;
				this.saveStatus = 'error';
			} finally {
				this.saving = false;
			}
		}
	}
};