from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Memory, MemoryFile
from django.core.files.uploadedfile import SimpleUploadedFile

class MemoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_create_memory_with_files(self):
        # Create a simple image file
        image_content = b'image_data'
        image = SimpleUploadedFile("test_image.jpg", image_content, content_type="image/jpeg")
        
        # Create a simple video file
        video_content = b'video_data'
        video = SimpleUploadedFile("test_video.mp4", video_content, content_type="video/mp4")

        data = {
            'title': 'Test Memory',
            'message': 'This is a test message',
            'display_style': 'grid',
            'files': [image, video]
        }

        response = self.client.post(reverse('memory-create'), data)
        self.assertEqual(response.status_code, 302)  # Redirects to success_url

        # Check Memory object
        memory = Memory.objects.filter(title='Test Memory').first()
        self.assertIsNotNone(memory)
        self.assertEqual(memory.user, self.user)

        # Check MemoryFile objects
        files = MemoryFile.objects.filter(memory=memory)
        self.assertEqual(files.count(), 2)
        
        image_file = files.get(file_type='image')
        self.assertTrue(image_file.file.name.endswith('.jpg'))
        
        video_file = files.get(file_type='video')
        self.assertTrue(video_file.file.name.endswith('.mp4'))

    def test_delete_memory(self):
        memory = Memory.objects.create(user=self.user, title='To Delete', message='Bye', display_style='grid')
        MemoryFile.objects.create(memory=memory, file='test.jpg', file_type='image')
        
        url = reverse('memory-delete', args=[memory.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.assertFalse(Memory.objects.filter(pk=memory.pk).exists())
        self.assertFalse(MemoryFile.objects.filter(memory=memory).exists())
