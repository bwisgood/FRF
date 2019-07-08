class ReadOnlyMixin(RetrieveAPIView, ListAPIView, APIView):
    """
    只读方法
    """
    pass


class AllMethodMixin(ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, DeleteAPIView, APIView):
    """
    所有方法
    """
    pass
