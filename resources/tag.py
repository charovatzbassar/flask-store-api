from flask.views import MethodView
from flask_smorest import Blueprint, abort
from schemas import TagSchema, TagAndItemSchema
from models import TagModel, StoreModel, ItemModel
from db import db
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
 
blp = Blueprint("tags", __name__, description="Operations on tags")

@blp.route("/store/<int:store_id>/tag")
class TagsInStore(MethodView):
    @blp.response(200, TagSchema(many=True))
    def get(self, store_id):
        store = StoreModel.query.get_or_404(store_id) # because we have lazy, this makes fetching much simpler
        return store.tags.all()
    
    @blp.arguments(TagSchema)
    @blp.response(201, TagSchema)
    def post(self, tag_data, store_id):
        # if TagModel.query.filter(TagModel.store_id == store_id, TagModel.name == tag_data["name"]).first():
        #     abort(400, message="A tag with that name already exists.")

        tag = TagModel(**tag_data, store_id=store_id)

        try:
            db.session.add(tag)
            db.session.commit()
        except SQLAlchemyError as e:
            abort(500, message=str(e))

        return tag

@blp.route("/tag/<int:tag_id>")
class Tag(MethodView):
    @blp.response(200, TagSchema)
    def get(self, tag_id):
        tag = TagModel.query.get_or_404(tag_id)
        return tag
    
    @blp.response(202, description="Delete a tag if no item is connected with it.", example={"message": "Tag deleted."})
    @blp.alt_response(404, description="Tag not found.")
    @blp.alt_response(400, description="Tag is assigned to one or more items.")
    def delete(self, tag_id):
        tag = TagModel.query.get_or_404(tag_id)

        if not tag.items:
            db.session.delete(tag)
            db.session.commit()
            return {"message": "Tag deleted."}
        
        abort(400, message="Could not delete tag. Make sure tag is not associated with any items.")
    
    
@blp.route("/item/<int:item_id>/tag/<int:tag_id>")
class LinkTagsToItem(MethodView):
    @blp.response(201, TagSchema)
    def post(self, item_id, tag_id):
        item = ItemModel.query.get_or_404(item_id)
        tag = TagModel.query.get_or_404(tag_id)

        if int(item.store_id) == int(tag.store_id):
            item.tags.append(tag)
            try:
                db.session.add(item)
                db.session.commit()
            except SQLAlchemyError as e:
                abort(500, message=str(e))
            
            return tag
        
        abort(400, message="You cannot assign a tag from a different store.")
    
    @blp.response(200, TagAndItemSchema)
    def delete(self, item_id, tag_id):
        item = ItemModel.query.get_or_404(item_id)
        tag = TagModel.query.get_or_404(tag_id)

        item.tags.remove(tag)

        try:
            db.session.add(item)
            db.session.commit()
        except SQLAlchemyError as e:
            abort(500, message=str(e))

        return {'message': 'Item removed from tag', 'item': item, 'tag': tag}
     