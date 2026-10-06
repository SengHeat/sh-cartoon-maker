from __future__ import annotations


class GroundProvider:
    def height_at(self,x:float,y:float)->float:raise NotImplementedError
    def normal_at(self,x:float,y:float)->tuple[float,float,float]:return (0.0,0.0,1.0)


class FlatGround(GroundProvider):
    def __init__(self,height:float=0.0):self.height=height
    def height_at(self,x:float,y:float)->float:return self.height


class EnvironmentGround(GroundProvider):
    """Ground adapter backed by an EnvironmentDefinition."""
    def __init__(self,environment:object):self.environment=environment
    def height_at(self,x:float,y:float)->float:return self.environment.ground_height(x,y)
    def normal_at(self,x:float,y:float)->tuple[float,float,float]:return self.environment.ground_normal(x,y)
