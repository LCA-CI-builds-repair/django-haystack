# "Hey, Django! Look at me, I'm an app! For Serious!"
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str
from django.utils.text import capfirst

from haystack.constants import DEFAULT_ALIAS
from haystack.exceptions import NotHandled, SpatialError
from haystack.utils import log as logging
from haystack.utils.app_loading import haystack_get_model

try:
    from geopy import distance as geopy_distance
except ImportError:
    geopy_distance = None


# Not a Django model, but tightly tied to them and there doesn't seem to be a
# better spot in the tree.
class SearchResult:
    """
    A single search result. The actual object is loaded lazily by accessing
    object; until then this object only stores the model, pk, and score.

    Note that iterating over SearchResults and getting the object for each
    result will do O(N) database queries, which may not fit your needs for
    performance.
    """

    def __init__(self, app_label, model_name, pk, score, **kwargs):
        self.app_label, self.model_name = app_label, model_name
        self.pk = pk
        self.score = score
        self._object = None
        self._model = None
        self._verbose_name = None
        self._additional_fields = []
        self._point_of_origin = kwargs.pop("_point_of_origin", None)
        self._distance = kwargs.pop("_distance", None)
        self.stored_fields = None
        self.log = self._get_log()

        for key, value in kwargs.items():
            if key not in self.__dict__:
                self.__dict__[key] = value
                self._additional_fields.append(key)

    def _get_log(self):
        return logging.getLogger("haystack")

    def __repr__(self):
        return "<SearchResult: %s.%s (pk=%r)>" % (
            self.app_label,
            self.model_name,
            self.pk,
        )

    def __str__(self):
        return force_str(self.__repr__())

    def __getattr__(self, attr):
        if attr == "__getnewargs__":
            raise AttributeError

        return self.__dict__.get(attr, None)

    def _get_searchindex(self):
        from haystack import connections

        return connections[DEFAULT_ALIAS].get_unified_index().get_index(self.model)

    searchindex = property(_get_searchindex)


    def content_type(self):
        """Returns the content type for the result's model instance."""
        if self.model is None:
            self.log.error("Model could not be found for SearchResult '%s'.", self)
            return ""

        return str(self.model._meta)

    def get_additional_fields(self):
        """
        Returns a dictionary of all of the fields from the raw result.

        Useful for serializing results. Only returns what was seen from the
        search engine, so it may have extra fields Haystack's indexes aren't
        aware of.
        """
        additional_fields = {}

        for fieldname in self._additional_fields:
            additional_fields[fieldname] = getattr(self, fieldname)

        return additional_fields

    def get_stored_fields(self):
        """
        Returns a dictionary of all of the stored fields from the SearchIndex.

        Useful for serializing results. Only returns the fields Haystack's
        indexes are aware of as being 'stored'.
        """
        if self._stored_fields is None:
            from haystack import connections

            try:
                index = (
                    connections[DEFAULT_ALIAS].get_unified_index().get_index(self.model)
                )
            except NotHandled:
                # Not found? Return nothing.
                return {}

            self._stored_fields = {}

            # Iterate through the index's fields, pulling out the fields that
            # are stored.
            for fieldname, field in index.fields.items():
                if field.stored is True:
                    self._stored_fields[fieldname] = getattr(self, fieldname, "")

        return self._stored_fields

    def __getstate__(self):
        """
        Returns a dictionary representing the ``SearchResult`` in order to
        make it pickleable.
        """
        # The ``log`` is excluded because, under the hood, ``logging`` uses
        # ``threading.Lock``, which doesn't pickle well.
        ret_dict = self.__dict__.copy()
        del ret_dict["log"]
        return ret_dict

    def __setstate__(self, data_dict):
        """
        Updates the object's attributes according to data passed by pickle.
        """
        self.__dict__.update(data_dict)
        self.log = self._get_log()


def reload_indexes(sender, *args, **kwargs):
    from haystack import connections

    for conn in connections.all():
        ui = conn.get_unified_index()
        # Note: Unlike above, we're resetting the ``UnifiedIndex`` here.
        # Thi gives us a clean slate.
        ui.reset()
