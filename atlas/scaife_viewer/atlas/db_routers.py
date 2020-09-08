# TODO: Document setting up ATLAS_DB_LABEL bits; possibly via appconf
ATLAS_DB_LABEL = "atlas"


class ATLASRouter:
    """
    A router to control all database operations on models in the
    library application.
    """

    route_app_labels = {"library"}

    def db_for_read(self, model, **hints):
        """
        Attempts to read library models go to ATLAS_DB_LABEL.
        """
        if model._meta.app_label in self.route_app_labels:
            return ATLAS_DB_LABEL
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write library models go to ATLAS_DB_LABEL.
        """
        if model._meta.app_label in self.route_app_labels:
            return ATLAS_DB_LABEL
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in library app is
        involved.
        """
        if (
            obj1._meta.app_label in self.route_app_labels
            or obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only add library apps to the ATLAS_DB_LABEL database.

        Do not add library apps to any other database.
        """
        if db == ATLAS_DB_LABEL:
            return app_label in self.route_app_labels
        elif app_label in self.route_app_labels:
            return db == ATLAS_DB_LABEL
        return None
