from .views import GetView, PostView, PutView, RetrieveView, DeleteView


class AllMethodMixin(GetView, PostView, PutView, RetrieveView, DeleteView):
    pass


class ReadOnlyMixin(GetView, RetrieveView):
    pass
