from django.db import models

# Create your models here.
from root.models import SimpleModel


class Newspaper(SimpleModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Publication(SimpleModel):
    newspaper = models.ForeignKey(Newspaper, on_delete=models.CASCADE)
    published_date = models.DateField()
    volume = models.IntegerField(null=True, blank=True)
    number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{}, Volumn {}, Number {}, Published {}'.format(self.newspaper.name, self.volume, self.number, self.published_date.strftime('%Y-%m-%d'))


class Article(SimpleModel):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    index = models.IntegerField()
    title = models.TextField()
    url = models.CharField(max_length=1024, default='')


class Paragraph(SimpleModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    index = models.IntegerField()
    content = models.TextField()

    percentage_maori = models.FloatField(null=True, blank=True)
    maori_word_count = models.IntegerField(null=True, blank=True)
    ambiguous_word_count = models.IntegerField(null=True, blank=True)
    other_word_count = models.IntegerField(null=True, blank=True)
    total_word_count = models.IntegerField(null=True, blank=True)
